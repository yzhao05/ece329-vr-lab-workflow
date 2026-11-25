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
    write_bytes(path, content.encode("utf-8"))


def write_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            tmp = Path(stream.name)
            stream.write(content)
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


def recap_path(pack, lab_id, status):
    contract = pack / "LabSpecs" / valid_id(lab_id) / "design-input/builder-gate1-input.json"
    document = json.loads(contract.read_text(encoding="utf-8-sig")).get("document", {}) if contract.is_file() else {}
    if document.get("source_design_id"):
        folder = Path(valid_id(document["source_design_id"]))
        fingerprint = (document.get("source_design") or {}).get("fingerprint")
    else:
        folder = Path("builder") / lab_id
        fingerprint = (status.get("evidence") or {}).get("compile_content_digest")
    if not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", fingerprint):
        raise ValueError("Cannot locate the accepted revision for the Gate 8 retrospective.")
    return Path("knowledge/newknowledge") / folder / (fingerprint + ".md")


def upload_marker(pack, lab_id):
    return pack / "BuildEvidence" / valid_id(lab_id) / "approval-turns/gate8-upload.pending.json"


def remember_upload(pack, lab_id, digest, request):
    path = upload_marker(pack, lab_id)
    saved = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    if saved.get("digest") != digest:
        saved = {"digest": digest}
    saved.update({key: value for key, value in request.items() if value is not None})
    write_json(path, saved)
    return saved


def finish_gate8(pack, lab_id, note, receipt, notes, upload_request):
    # Called under the approval lock. Keep a recoverable draft until publication
    # succeeds, including across a crash just after the native gate is approved.
    status = json.loads(labflow(pack, "status", "--lab-id", lab_id))
    rel = recap_path(pack, lab_id, status)
    pending = receipt.parent / "gate8-retrospective.pending.json"
    prior = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else None
    if prior is not None and prior != {"gate": 8, "note": note}:
        raise ValueError("This user message is already bound to a different approval.")
    target = ROOT / rel
    if status["workflow_complete"] and not pending.exists() and target.is_file() and target.stat().st_size:
        if upload_request is not None:
            remember_upload(pack, lab_id, status["evidence"]["compile_content_digest"], upload_request)
        return f"Gate 8 completed. knowledge_update: {rel.as_posix()}"
    complete = status["workflow_complete"]
    draft = json.loads(pending.read_text(encoding="utf-8")) if pending.exists() else {}
    state_hash = hashlib.sha256((pack / "LabSpecs" / lab_id / "workflow_state.json").read_bytes())
    for record in sorted((receipt.parent.parent / "handbooks").glob("*.json")):
        state_hash.update(record.name.encode("utf-8") + b"\0" + hashlib.sha256(record.read_bytes()).digest())
    state_digest = state_hash.hexdigest()
    retry = (draft.get("receipt") == receipt.name and draft.get("state_digest") == state_digest)
    if not complete:
        if prior is not None and not retry:
            raise ValueError("Gate 8 requires a fresh user approval for its current state.")
        if status.get("current_gate") != 8 or not status.get("gate_ready_for_approval"):
            raise ValueError("Gate 8 is not ready for approval: " + "; ".join(status.get("gate_blockers", [])))
    if draft and (complete or retry):
        if draft["path"] != rel.as_posix():
            raise ValueError("Pending retrospective does not match the accepted revision.")
        content = draft["notes"]
    else:
        content = notes.read_text(encoding="utf-8-sig").strip() if notes else ""
        if not content:
            raise ValueError("Gate 8 needs the agent's nonempty UTF-8 retrospective via --notes FILE.")
        write_json(pending, {"path": rel.as_posix(), "notes": content, "receipt": receipt.name, "state_digest": state_digest})
    if upload_request is not None:
        remember_upload(pack, lab_id, status["evidence"]["compile_content_digest"], upload_request)
    if not complete:
        write_json(receipt, {"gate": 8, "note": note})
        labflow(pack, "approve-gate", "--lab-id", lab_id, "--gate", "8", "--note", note)
        accepted = json.loads(labflow(pack, "status", "--lab-id", lab_id))
        if not accepted.get("workflow_complete") or recap_path(pack, lab_id, accepted) != rel:
            raise ValueError("Gate 8 acceptance changed. Revalidate the current revision before publishing the retrospective.")
    write_text(target, content + "\n")
    pending.unlink()
    return f"Gate 8 completed. knowledge_update: {rel.as_posix()}"


def approve_user_gate(pack, lab_id, gate, note, turn_id, notes=None, upload_request=None):
    """Bind a real user message to one gate, including across CLI restarts."""
    if not turn_id or not turn_id.strip() or len(turn_id) > 256:
        raise ValueError("Provide the same --turn-id for every action from this user message.")
    pack = native_path(pack)
    if not (pack / "LabSpecs" / valid_id(lab_id) / "workflow_state.json").is_file():
        raise ValueError("Builder run not found.")
    receipts = pack / "BuildEvidence" / lab_id / "approval-turns"
    receipt = receipts / (hashlib.sha256(turn_id.encode()).hexdigest() + ".json")
    with lock(receipts / "approve.lock"):
        if gate == 8:
            return finish_gate8(pack, lab_id, note, receipt, notes, upload_request)
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
    if data.get("stage") == "acceptance_revalidation":
        return "Builder · Gate 6 · 场景需要重新验收"
    if data.get("stage") == "handbooks_revalidation":
        return "Builder · Gate 8 · 手册需要重新验证"
    if data.get("retrospective_pending"):
        return "Builder · Gate 8 · 验收通过，待归档复盘"
    if data.get("upload_pending"):
        return "Builder · Gate 8 · 验收通过，上传副本待整理"
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


def unified_builder_status(pack, data):
    if data.get("workflow_complete"):
        lab_id = data["lab_id"]
        rel = recap_path(pack, lab_id, data)
        target = ROOT / rel
        pending = pack / "BuildEvidence" / lab_id / "approval-turns/gate8-retrospective.pending.json"
        if pending.exists() or not target.is_file() or not target.stat().st_size:
            data.setdefault("approved_gates", data.get("gate_sequence", []))
            data.update(workflow_complete=False, retrospective_pending=True, stage="retrospective_pending",
                        current_gate=8, next_action="Archive the Gate 8 retrospective using the recorded approval.")
        else:
            data["knowledge_update"] = rel.as_posix()
            marker = upload_marker(pack, lab_id)
            try:
                saved = json.loads(marker.read_text(encoding="utf-8"))
            except FileNotFoundError:
                saved = None
            if saved and saved["digest"] == data["evidence"]["compile_content_digest"]:
                data.setdefault("approved_gates", data.get("gate_sequence", []))
                data.update(workflow_complete=False, upload_pending=True, stage="upload_pending",
                            current_gate=8, next_action="Retry prepare-upload for the accepted build.")
    return data


def read_builder_status(pack, lab_id, fingerprint=None):
    data = unified_builder_status(pack, json.loads(labflow(pack, "status", "--lab-id", lab_id)))
    fields = ("lab_id", "current_gate", "current_gate_name", "workflow_complete", "accepted",
              "gate_ready_for_approval", "gate8_step", "migration_required", "stage")
    summary = {key: data.get(key) for key in fields}
    for key in ("retrospective_pending", "upload_pending", "knowledge_update"):
        if key in data:
            summary[key] = data[key]
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


def missing_workspace_status(lab_id):
    return {"stage": "workspace_missing", "lab_id": lab_id, "current_gate": None,
            "workflow_complete": False, "approved_gates": [], "status_line": "Builder · 原工作区缺失，待恢复"}


def active_builder(state, key, fingerprint):
    if not fingerprint:
        return None
    try:
        marker = json.loads((state / "runs" / key / "active.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if marker["fingerprint"] != fingerprint:
        return None
    pack = run_directory(state, key, fingerprint)
    if not (native_path(pack) / "LabSpecs" / valid_id(marker["lab_id"]) / "workflow_state.json").is_file():
        return {**missing_workspace_status(marker["lab_id"]), "source_fingerprint": fingerprint}
    return read_builder_status(pack, marker["lab_id"], fingerprint)
