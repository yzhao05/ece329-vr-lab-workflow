import json
from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import workspace


@pytest.mark.parametrize(("stage", "gate"), [("acceptance_revalidation", 6), ("handbooks_revalidation", 8)])
def test_agent_reports_the_same_revalidation_gate_as_the_viewer(stage, gate):
    line = workspace.builder_progress({"current_gate": 8, "stage": stage})
    assert f"Gate {gate}" in line and "重新" in line


@pytest.mark.parametrize("linked", [True, False])
def test_gate8_approval_publishes_recap_and_recovers_after_write_failure(tmp_path, monkeypatch, linked):
    pack = tmp_path / "run"
    spec = pack / "LabSpecs" / "test_lab"
    spec.mkdir(parents=True)
    (spec / "workflow_state.json").write_text("{}")
    fingerprint = "a" * 64
    if linked:
        workspace.write_json(spec / "design-input/builder-gate1-input.json", {"document": {
            "source_design_id": "design_1", "source_design": {"fingerprint": fingerprint}}})
    status = {"lab_id": "test_lab", "current_gate": 8, "workflow_complete": False,
              "gate_ready_for_approval": True, "evidence": {"compile_content_digest": fingerprint}}
    calls = []

    def native(pack, action, *args):
        if action == "status":
            return json.dumps(status)
        assert action == "approve-gate"
        calls.append(action)
        if len(calls) == 1:
            raise OSError("native save interrupted")
        status.update(workflow_complete=True, current_gate=None)
        return "Approved"

    monkeypatch.setattr(workspace, "ROOT", tmp_path)
    monkeypatch.setattr(workspace, "labflow", native)
    notes = tmp_path / "notes.md"
    notes.write_text("  已修复路径，XR 待实机验证。\n", encoding="utf-8")
    args = (pack, "test_lab", 8, "同意", "turn8")
    status["gate_ready_for_approval"] = False
    with pytest.raises(ValueError, match="not ready"):
        workspace.approve_user_gate(*args, notes)
    status["gate_ready_for_approval"] = True
    with pytest.raises(ValueError, match="--notes"):
        workspace.approve_user_gate(*args)
    assert calls == []
    folder = "design_1" if linked else "builder/test_lab"
    target = tmp_path / "knowledge/newknowledge" / folder / (fingerprint + ".md")
    with pytest.raises(OSError, match="native save interrupted"):
        workspace.approve_user_gate(*args, notes)
    assert not status["workflow_complete"] and not target.exists()
    notes.unlink()
    write = workspace.write_text

    def fail_publication(path, content):
        if path == target:
            raise OSError("disk full")
        write(path, content)

    with monkeypatch.context() as patch:
        patch.setattr(workspace, "write_text", fail_publication)
        with pytest.raises(OSError, match="disk full"):
            workspace.approve_user_gate(*args)
    assert not target.exists()
    pending = workspace.unified_builder_status(pack, status.copy())
    assert pending["retrospective_pending"] and not pending["workflow_complete"]
    workspace.approve_user_gate(*args)
    workspace.approve_user_gate(*args)
    assert calls == ["approve-gate", "approve-gate"]
    assert target.read_text(encoding="utf-8") == "已修复路径，XR 待实机验证。\n"
    complete = workspace.unified_builder_status(pack, status.copy())
    assert complete["workflow_complete"] and tmp_path / complete["knowledge_update"] == target
