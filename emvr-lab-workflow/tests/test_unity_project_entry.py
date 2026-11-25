import json
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


@pytest.mark.parametrize("gate,foundation,allowed", [(4, "pending", True), (5, "pending", True),
                                                     (5, "passed", False), (8, "passed", False)])
def test_reopening_and_upgrading_editor_tools(tmp_path, gate, foundation, allowed):
    pack = make_run(tmp_path, "old")
    status = {"current_gate": gate, "evidence": {"gate5_foundation": foundation}}
    native = pack / "Tools/labflow/labflow.py"
    native.parent.mkdir(parents=True)
    native.write_text(f"print({json.dumps(status)!r})")
    assets = pack / "UnityProject/Assets"
    result = lookup(tmp_path, pack)
    assert result.returncode == 0, result.stderr
    assert not assets.exists()
    setup = subprocess.run([sys.executable, str(SCRIPT), str(pack), "prepare-editor", "--lab-id", LAB],
                           capture_output=True, encoding="utf-8")
    assert (setup.returncode == 0) == allowed, setup.stderr
    assert (assets / "EmvrWorkflowPreview/Editor/EmvrSceneLayoutPreview.cs").is_file() == allowed
    assert (assets / "EmvrImportProtection/Editor/EmvrXrImportSaveGuard.cs").is_file() == allowed


def test_ambiguous_lab_requires_explicit_workspace(tmp_path):
    first = make_run(tmp_path, "first")
    second = make_run(tmp_path, "second")
    result = lookup(tmp_path)
    assert result.returncode and "Multiple workspaces" in result.stderr
    assert str(first) in result.stderr and str(second) in result.stderr


@pytest.mark.skipif(os.name != "nt", reason="Windows Unity path limit")
def test_scaffold_stops_before_native_command_and_reads_asset_via_short_entry(tmp_path):
    pack = make_run(tmp_path, "deep_run_" * 9)
    imported = Path("Assets/Generated") / LAB / "ApprovedDependencies/EMVRRoom/Lighting/RoomLighting.lighting"
    project = pack / "UnityProject"
    real = Path("\\\\?\\" + str(project / imported))
    assert len(str(project / imported)) >= 260
    # The default entry parent cannot be used.
    (tmp_path / "local").write_text("occupied")
    env = {**os.environ, "LOCALAPPDATA": str(tmp_path / "local"), "PYTHONUTF8": "1"}
    env.pop("EMVR_UNITY_ENTRY_DIR", None)
    native = pack / "Tools/labflow/labflow.py"
    native.parent.mkdir(parents=True)
    native.write_text("import sys\nprint('{\"current_gate\":4}' if 'status' in sys.argv else 'native scaffold')")
    args = [sys.executable, str(SCRIPT), str(pack), "scaffold", "--lab-id", LAB]
    blocked = subprocess.run(args, env=env, capture_output=True, encoding="utf-8")
    assert blocked.returncode and "Unity Editor entry unavailable" in blocked.stderr
    assert "native scaffold" not in blocked.stdout
    source = pack / "ApprovedAssets/EMVRRoom/Lighting/RoomLighting.lighting"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"lighting fixture")
    too_long = subprocess.run([*args[:2], "--entry-dir", str(tmp_path / ("u" * 160)), *args[2:]],
                              env=env, capture_output=True, encoding="utf-8")
    assert too_long.returncode and "MAX_PATH" in too_long.stderr and "native scaffold" not in too_long.stdout
    real.parent.mkdir(parents=True)
    real.write_bytes(source.read_bytes())
    result = subprocess.run([*args[:2], "--entry-dir", str(tmp_path / "u"), *args[2:]],
                            env=env, capture_output=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    entry = Path(result.stdout.split("unity_editor_project: ")[1].strip())
    assert entry.samefile(project) and len(str(entry / imported)) < 260
    assert (entry / imported).read_bytes() == b"lighting fixture"
    # Later imports can add assets outside the Gate 5 source templates.
    extra = real.parent / ("additional-component-" * 5 + ".cs")
    extra.write_bytes(b"// imported component")
    oversized = subprocess.run([*args[:2], "--entry-dir", str(tmp_path / "u"), str(pack), "unity-project"],
                               env=env, capture_output=True, encoding="utf-8")
    assert oversized.returncode and extra.name in oversized.stderr and "MAX_PATH" in oversized.stderr


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
