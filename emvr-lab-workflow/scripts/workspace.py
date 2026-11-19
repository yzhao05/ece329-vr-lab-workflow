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


def labflow(pack, *args):
    pack = native_path(pack)
    command = [sys.executable, str(pack / "Tools/labflow/labflow.py"), "--project-root", str(pack), *args]
    proc = subprocess.run(command, cwd=pack, encoding="utf-8", capture_output=True,
                          env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    if proc.returncode:
        raise ValueError((proc.stderr or proc.stdout).strip())
    return proc.stdout


def run_directory(state, key, fingerprint):
    digest = hashlib.sha256((key + ":" + fingerprint).encode("utf-8")).digest()
    name = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    return state / "builds" / name / BASE.name


def read_builder_status(pack, lab_id, fingerprint=None):
    data = json.loads(labflow(pack, "status", "--lab-id", lab_id))
    fields = ("lab_id", "current_gate", "current_gate_name", "workflow_complete", "accepted",
              "gate_ready_for_approval", "gate8_step", "migration_required", "stage")
    summary = {key: data.get(key) for key in fields}
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
