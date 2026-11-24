import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("linked", [False, True])
def test_gate8_cli_creates_both_uploads_and_retries_without_approval(tmp_path, linked):
    scripts = tmp_path / "emvr-lab-workflow/scripts"
    shutil.copytree(Path(__file__).resolve().parents[1] / "scripts", scripts,
                    ignore=shutil.ignore_patterns("__pycache__"))
    pack = tmp_path / "pack"
    lab = "test_lab"
    digest = "a" * 64
    version = Path(lab) / digest
    spec = pack / "LabSpecs" / lab

    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    write(spec / "workflow_state.json", "{}")
    recap = Path("builder") / lab / (digest + ".md")
    if linked:
        recap = Path("design_123") / ("b" * 64 + ".md")
        write(spec / "design-input/builder-gate1-input.json", json.dumps({"document": {
            "source_design_id": "design_123", "source_design": {"fingerprint": "b" * 64}}}))
    status = {"lab_id": lab, "workflow_complete": False, "current_gate": 8,
              "gate_ready_for_approval": True, "evidence": {"compile_content_digest": digest}}
    write(pack / "status.json", json.dumps(status))
    write(pack / "Tools/labflow/labflow.py", """
import json,sys
from pathlib import Path
p = Path('status.json')
s = json.loads(p.read_text())
if 'approve-gate' in sys.argv:
    assert not s['workflow_complete']
    s.update(workflow_complete=True, current_gate=None)
    p.write_text(json.dumps(s))
print(json.dumps(s))
""")
    notes = tmp_path / "notes.md"
    write(notes, "Lab retrospective")
    write(tmp_path / "reusable-code/newcode" / version / "Scripts/Lab.cs", "archived")
    project = pack / "UnityProject"
    write(project / "Assets/Editor/Build.cs", "editor script")
    write(project / "Assets/Editor/Build.cs.meta", "editor guid")
    write(project / "Assets/Editor.meta", "directory guid")
    write(project / "Assets/main.unity", "large scene")
    write(project / "LocalPackages/pkg/Runtime.cs", "local package")
    write(project / "Packages/manifest.json", '{"dependencies":{"pkg":"file:../LocalPackages/pkg"}}')
    write(project / "ProjectSettings/ProjectVersion.txt", "2022")
    write(tmp_path / "knowledge/newknowledge/other-run.md", "unrelated")
    state = tmp_path / "private"
    prefix = [sys.executable, str(scripts / "builder.py"), "--state-dir", str(state), str(pack)]
    retry = ["prepare-upload", "--lab-id", lab, "--knowledge-file", "supplement.md"]
    approve = ["approve-gate", "--lab-id", lab, "--gate", "8", "--turn-id", "u8",
               "--note", "accepted", "--notes", str(notes), "--knowledge-file", "supplement.md"]
    if linked:
        for args in (retry, approve):
            args.extend(["--submitter", "张三"])
    def run(args):
        return subprocess.run(prefix + args, capture_output=True, encoding="utf-8")

    assert run(retry).returncode != 0
    assert run(approve).returncode != 0  # Acceptance succeeds, missing supplement prevents publication.
    assert json.loads((pack / "status.json").read_text())["workflow_complete"]
    query = ["status", "--lab-id", lab]
    pending = json.loads(run(query).stdout)
    assert pending["upload_pending"] and not pending["workflow_complete"]
    assert pending["current_gate"] == 8 and "上传副本待整理" in pending["status_line"]
    assert not list((state / "uploads" / lab).iterdir())
    write(tmp_path / "knowledge/newknowledge/supplement.md", "this run")
    result = run(["prepare-upload", "--lab-id", lab] if linked else approve)
    assert result.returncode == 0, result.stderr
    delivery = json.loads(result.stdout)
    assert json.loads(run(query).stdout)["workflow_complete"]
    code, knowledge = map(Path, (delivery["newcode"], delivery["newknowledge"]))
    name = "张三" if linked else lab
    assert (code.name, knowledge.name) == (name + "_newcode", name + "_newknowledge")
    assert (code / version / "Scripts/Lab.cs").read_text() == "archived"
    unity = code / version / "UnityProject"
    for relative in ["Assets/Editor/Build.cs", "Assets/Editor/Build.cs.meta", "Assets/Editor.meta",
                     "LocalPackages/pkg/Runtime.cs", "Packages/manifest.json", "ProjectSettings/ProjectVersion.txt"]:
        assert (unity / relative).read_bytes() == (project / relative).read_bytes()
    assert not (unity / "Assets/main.unity").exists()
    assert {p.relative_to(knowledge) for p in knowledge.rglob("*") if p.is_file()} == {recap, Path("supplement.md")}
    assert (knowledge / recap).read_bytes() == (tmp_path / delivery["knowledge_update"]).read_bytes()
