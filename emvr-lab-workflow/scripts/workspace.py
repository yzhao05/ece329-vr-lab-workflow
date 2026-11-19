"""Shared package locations, atomic file writes and native Builder commands."""
import base64
import hashlib
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parent
SNAPSHOT_VERSION = 2
DEFAULT_STATE = ROOT / "state" if (ROOT / "state").is_dir() else SKILL / "state"
BASE = ROOT / "reusable-code/EMVR_Blind_BuilderPack"


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=2)


def write_json(path, data):
    write_text(path, dump(data))


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(content.encode("utf-8"))
        os.replace(tmp, path)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)



@contextmanager
def lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield  # Closing the file releases the process lock, including on failure.


def valid_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
        raise ValueError("Invalid design ID")
    return value


def native_path(path):
    """Preserve deep Unity asset paths on Windows installations using MAX_PATH."""
    raw = str(path.absolute())
    if os.name != "nt" or raw.startswith("\\\\?\\"):
        return path
    if raw.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + raw[2:])
    return Path("\\\\?\\" + raw)


def publish_directory(staged, target):
    """Atomically publish after Windows releases transient staging-file handles."""
    for attempt in range(6):
        try:
            staged.rename(target)
            return
        except PermissionError as error:
            if getattr(error, "winerror", None) not in (5, 32, 33) or attempt == 5:
                raise
            time.sleep(0.1 * 2**attempt)


def builder_command(pack, *args):
    pack = native_path(pack)
    script = pack / "Tools/labflow/labflow.py"
    # Previously published runs freeze their own tools at Gate 0. Use the
    # compatible reader for that exact release without rewriting frozen bytes.
    if hashlib.sha256(script.read_bytes()).hexdigest() == "d86e54ca5488871ac79a6921c17efcd751d6c086fdcf8d86e5e6980a174c19f6":
        script = BASE / "Tools/labflow/labflow.py"
    return [sys.executable, str(script), "--project-root", str(pack), *args]


def labflow(pack, *args):
    pack = native_path(pack)
    command = builder_command(pack, *args)
    proc = subprocess.run(command, cwd=pack, encoding="utf-8", capture_output=True,
                          env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    if proc.returncode:
        raise ValueError((proc.stderr or proc.stdout).strip())
    return proc.stdout


def run_directory(state, key, fingerprint):
    digest = hashlib.sha256((key + ":" + fingerprint).encode("utf-8")).digest()
    name = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    return state / "builds" / name / BASE.name


def approve_user_gate(pack, lab_id, gate, note, turn_id):
    """Bind a real user message to one gate, including across CLI restarts."""
    if not turn_id or not turn_id.strip() or len(turn_id) > 256:
        raise ValueError("Provide the same --turn-id for every action from this user message.")
    pack = native_path(pack)
    if not (pack / "LabSpecs" / valid_id(lab_id) / "workflow_state.json").is_file():
        raise ValueError("Builder run not found.")
    receipts = pack / "BuildEvidence" / lab_id / "approval-turns"
    receipt = receipts / (hashlib.sha256(turn_id.encode()).hexdigest() + ".json")
    with lock(receipts / "approve.lock"):
        if receipt.exists():
            previous = json.loads(receipt.read_text(encoding="utf-8"))
            if previous != {"gate": gate, "note": note}:
                raise ValueError("This user message is already bound to a different approval.")
            status = read_builder_status(pack, lab_id)
            if gate in status["approved_gates"]:
                return f"Gate {gate} approval already recorded."
            # A revision may have invalidated the approval, or a previous
            # attempt may have stopped before committing. Both need a new turn.
            raise ValueError(f"Gate {gate} requires a fresh user approval for its current state.")
        write_json(receipt, {"gate": gate, "note": note})
        return labflow(pack, "approve-gate", "--lab-id", lab_id, "--gate", str(gate), "--note", note)


def builder_progress(data):
    gate = data.get("current_gate")
    if data.get("workflow_complete"):
        return "Builder · Gate 8 · 已完成"
    if data.get("migration_required") or gate is None:
        return "Builder · 待核对工作区状态"
    blocked = (data.get("blocker_recovery") or {}).get("active")
    status = "受阻" if blocked else "待用户批准" if data.get("gate_ready_for_approval") else "进行中"
    catalog = json.loads((ROOT / "web/stages.json").read_text(encoding="utf-8"))
    name = next((item["title"] for item in catalog["builder"] if item["gate"] == gate),
                data.get("current_gate_name") or "")
    return f"Builder · Gate {gate} · {name} · {status}"


def read_builder_status(pack, lab_id, fingerprint=None):
    data = json.loads(labflow(pack, "status", "--lab-id", lab_id))
    fields = ("lab_id", "current_gate", "current_gate_name", "workflow_complete", "accepted",
              "gate_ready_for_approval", "gate8_step", "migration_required", "stage")
    summary = {key: data.get(key) for key in fields}
    summary["status_line"] = builder_progress(data)
    # Older run packs predate the normalized approval list. current_gate is
    # the first gate their own validator considers unapproved.
    sequence = data.get("gate_sequence", [])
    current = data.get("current_gate")
    if "approved_gates" in data:
        summary["approved_gates"] = data["approved_gates"]
    elif data.get("workflow_complete"):
        summary["approved_gates"] = sequence
    else:
        summary["approved_gates"] = sequence[:sequence.index(current)] if current in sequence else []
    if fingerprint:
        summary["source_fingerprint"] = fingerprint
    return summary


def active_builder(state, key, fingerprint):
    if not fingerprint:
        return None
    try:
        marker = json.loads((state / "runs" / key / "active.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if marker["fingerprint"] != fingerprint:
        return None
    return read_builder_status(run_directory(state, key, fingerprint), marker["lab_id"], fingerprint)
