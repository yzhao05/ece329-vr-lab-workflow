import os
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "builder.py"
LAB = "ece329_solenoid_current"


def make_run(root, revision):
    pack = root / "builds" / revision / "EMVR_Blind_BuilderPack"
    state = pack / "LabSpecs" / LAB / "workflow_state.json"
    state.parent.mkdir(parents=True)
    state.write_text("{}")
    settings = pack / "UnityProject" / "ProjectSettings"
    settings.mkdir(parents=True)
    (settings / "ProjectVersion.txt").write_text("m_EditorVersion: 2022.3.62f3c1")
    return pack


def lookup(root, workspace=LAB):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--state-dir", str(root), str(workspace), "unity-project"],
        cwd=root, env={**os.environ, "LOCALAPPDATA": str(root / "local")},
        capture_output=True, encoding="utf-8",
    )


def test_ambiguous_lab_requires_explicit_workspace(tmp_path):
    first = make_run(tmp_path, "first")
    second = make_run(tmp_path, "second")
    result = lookup(tmp_path)
    assert result.returncode and "Multiple workspaces" in result.stderr
    assert str(first) in result.stderr and str(second) in result.stderr


@pytest.mark.skipif(os.name != "nt", reason="NTFS directory junction")
def test_desktop_entry_survives_process_exit_and_preserves_collisions(tmp_path):
    pack = make_run(tmp_path, "first")
    first = lookup(tmp_path)
    assert first.returncode == 0, first.stderr
    entry = Path(first.stdout.strip())
    assert entry.is_relative_to(tmp_path / "local")
    assert entry.samefile(pack / "UnityProject")
    second = lookup(tmp_path, pack)
    assert second.returncode == 0 and second.stdout == first.stdout
    entry.rmdir()  # Remove just the test junction.
    entry.mkdir()
    (entry / "keep.txt").write_text("unrelated directory")
    collision = lookup(tmp_path)
    assert collision.returncode and "occupied" in collision.stderr
    assert (entry / "keep.txt").read_text() == "unrelated directory"
    assert (pack / "UnityProject/ProjectSettings/ProjectVersion.txt").is_file()
