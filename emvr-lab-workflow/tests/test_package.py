"""Cross the public agent, course-library, static-viewer and Builder boundaries."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tarfile
from contextlib import contextmanager
from urllib.request import ProxyHandler, build_opener
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "emvr-lab-workflow"
sys.path[:0] = [str(SKILL / "design/src"), str(SKILL / "design")]
from ece329_workflow.store import SQLiteSessionStore
from ece329_workflow.models import DesignSession, InteractionState, WorkflowStatus, Stage
from tools.export_emvr34_regression import completed_magnetic_engine


def cli(tmp, *args, stdin=None, ok=True):
    run = subprocess.run([sys.executable, str(SKILL / "scripts/workflow.py"), "--state-dir",
        str(tmp / "private"), "--web-dir", str(tmp / "public"), *args], cwd=tmp,
        input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None, text=True, encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"}, capture_output=True)
    if ok:
        assert run.returncode == 0, run.stderr
        return json.loads(run.stdout)
    assert run.returncode != 0
    return run.stderr


def viewer_command(tmp, *args):
    result = subprocess.run([sys.executable, str(SKILL / "scripts/viewer.py"), "--state-dir",
        str(tmp / "private"), "--web-dir", str(tmp / "public"), *args], cwd=tmp,
        capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    return result


@contextmanager
def page(tmp, *target):
    shutil.copytree(ROOT / "web", tmp / "public", ignore=shutil.ignore_patterns("data"), dirs_exist_ok=True)
    try:
        opened = json.loads(viewer_command(tmp, "open", "--url-only", *target).stdout)
        yield opened
    finally:
        viewer_command(tmp, "close")


def get(url, path):
    with build_opener(ProxyHandler({})).open(urljoin(url, path), timeout=30) as response:
        return json.load(response)


def test_agent_flow(tmp_path, monkeypatch):
    monkeypatch.setenv("ECE329_FEEDBACK_REASONING_EFFORT", "obsolete-offline-setting")
    monkeypatch.setenv("PYTHONIOENCODING", "gbk")
    created = cli(tmp_path, "create", "探索长螺线管中心的磁场与电流")
    key = created["design_id"]
    assert "Gate 1/7" in created["status_line"]
    assert created["stage_payload"]["emvr_formula_phase"] == "FORMULA_CANDIDATES_PRESENTED"
    assert "interpretation" not in created and "design_access_token" not in created
    action = {"type": "SELECT_EMVR_FORMULAS", "content": {
        "primary_profile_ids": ["FD13_CURRENT_SHEET_SOLENOID"], "primary_formula_ids": ["long_solenoid_field"]}}
    request = {"message": "选择长螺线管内部磁场公式", "turn_id": "example-turn-1",
               "interpretation": {"intent": "ANSWER_CURRENT_QUESTION", "confidence": 1,
                                  "semantic_updates": {"emvr_formula_actions": [action]}}}
    turn = cli(tmp_path, "turn", key, "--stdin-json", stdin=request)
    saved = SQLiteSessionStore(tmp_path / "private/design.sqlite3").get(key)
    assert saved.history[-1]["user_message"] == request["message"]
    assert turn["revision"] > created["revision"]
    assert "Gate 1/7" in turn["status_line"]
    assert turn["stage_payload"]["emvr_formula_phase"] != "FORMULA_CANDIDATES_PRESENTED"
    assert cli(tmp_path, "turn", key, "--stdin-json", stdin=request)["revision"] == turn["revision"]
    view = json.loads((tmp_path / "public/data" / (key + ".json")).read_text(encoding="utf-8"))
    assert len(view["flow"]) == 7 and view["evidence"]
    assert any(note["label"] == "已选主公式" for note in view["notes"])
    assert set(view) == {"design_id", "revision", "flow", "builder", "evidence", "notes", "check"}
    assert "确认" in cli(tmp_path, "export", key, ok=False)
    assert not (tmp_path / "private/handoffs").exists()


def test_directory_publication_retries_a_windows_lock(tmp_path, monkeypatch):
    sys.path.insert(0, str(SKILL / "scripts"))
    import workspace
    staged, target = tmp_path / "staged", tmp_path / "published"
    staged.mkdir()
    (staged / "ready.txt").write_text("ready")
    rename = Path.rename
    attempts = []

    def briefly_locked(source, destination):
        attempts.append(destination)
        if len(attempts) == 1:
            error = PermissionError("directory temporarily locked")
            error.winerror = 5
            raise error
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", briefly_locked)
    workspace.publish_directory(staged, target)
    assert attempts == [target, target]
    assert (target / "ready.txt").read_text() == "ready"


def test_course_identity_is_one_discussion(tmp_path):
    from ece329_workflow.engine import _emvr_stage_entry_output
    from ece329_workflow.dialogue_state import save_pending_action
    from ece329_workflow.builder_requirements import builder_requirement_values

    stage = Stage.COURSE_MAPPING_AND_DIRECTION
    title = "长螺线管中心磁场与电流"
    lab = "ece329_solenoid_current"
    store = SQLiteSessionStore(tmp_path / "private/design.sqlite3")
    for key, message, fields in (
        ("title_only", "就叫长螺线管中心磁场与电流吧", {"lab_title": title}),
        ("both_fields", "就叫长螺线管中心磁场与电流吧，内部编号用 ece329_solenoid_current 就好",
         {"lab_title": title, "lab_id": lab}),
    ):
        session = DesignSession(key, InteractionState.EMVR_DIRECT, current_stage_index=list(Stage).index(stage))
        save_pending_action(session, stage, _emvr_stage_entry_output(session, stage))
        store.save(session)
        request = {"message": message, "turn_id": "identity-turn", "interpretation": {
            "intent": "ANSWER_CURRENT_QUESTION", "confidence": 1,
            "semantic_updates": {"stage_field_updates": [
                {"field": field, "operation": "REPLACE", "value": value} for field, value in fields.items()]}}}
        reply = cli(tmp_path, "turn", key, "--stdin-json", stdin=request)
        saved = store.get(key)
        values = builder_requirement_values(saved)
        assert values["lab_title"] == title
        assert saved.history[-1]["user_message"] == message
        pending = reply["next_input"]
        if key == "title_only":
            assert not values.get("lab_id")
            assert pending["answer_fields"] == ["lab_id"]
        else:
            assert values["lab_id"] == lab
            assert not {"lab_id", "lab_title"}.intersection(pending.get("answer_fields", []))
        assert cli(tmp_path, "turn", key, "--stdin-json", stdin=request)["revision"] == reply["revision"]


def test_one_user_message_cannot_approve_two_builder_gates(tmp_path, monkeypatch):
    import pytest
    sys.path.insert(0, str(SKILL / "scripts"))
    import workspace
    state = tmp_path / "LabSpecs/course_lab/workflow_state.json"
    state.parent.mkdir(parents=True)
    state.write_text("{}")
    approvals = []
    monkeypatch.setattr(workspace, "labflow", lambda pack, *args: approvals.append(args))
    monkeypatch.setattr(workspace, "read_builder_status", lambda *args: {"approved_gates": [1]})
    def approve(gate, turn):
        return workspace.approve_user_gate(tmp_path, "course_lab", gate, "继续", turn)
    approve(1, "user-message-1")
    approve(1, "user-message-1")
    with pytest.raises(ValueError, match="already bound"):
        approve(2, "user-message-1")
    monkeypatch.setattr(workspace, "read_builder_status", lambda *args: {"approved_gates": []})
    with pytest.raises(ValueError, match="fresh user approval"):
        approve(1, "user-message-1")
    approve(2, "user-message-2")
    assert len(approvals) == 2


def test_finished_handoff(tmp_path):
    _, session = completed_magnetic_engine()
    session._store_snapshot = None
    SQLiteSessionStore(tmp_path / "private/design.sqlite3").save(session)
    key = session.design_id
    exported = cli(tmp_path, "export", key)
    bundle = Path(exported["artifacts"])
    assert all((bundle / filename).read_bytes().startswith(b"%PDF") for filename in
               ("design.pdf", "builder-gate1-input.pdf"))
    (bundle / "design.pdf").unlink()
    (bundle / "builder-gate1-input.pdf").write_bytes(b"%PDF-1.4\ninterrupted")
    assert cli(tmp_path, "find-handoff", key, "--revision", str(exported["revision"]))["candidates"] == []
    assert cli(tmp_path, "export", key)["artifacts"] == str(bundle)
    assert (bundle / "design.pdf").read_bytes().startswith(b"%PDF")
    assert (bundle / "builder-gate1-input.pdf").read_bytes().rstrip().endswith(b"%%EOF")
    assert len(cli(tmp_path, "find-handoff", key, "--revision", str(exported["revision"]))["candidates"]) == 1
    machine_copy = bundle / "builder-gate1-input.json"
    approved_input = machine_copy.read_bytes()
    machine_copy.write_text('{"historical":"previous export"}', encoding="utf-8")
    corrected = Path(cli(tmp_path, "export", key)["artifacts"])
    assert corrected != bundle and (corrected / machine_copy.name).read_bytes() == approved_input
    assert json.loads(machine_copy.read_text(encoding="utf-8")) == {"historical": "previous export"}
    machine_copy.write_bytes(approved_input)
    # A user may keep notes next to the PDFs. Only the approved handoff goes to Builder.
    (bundle / "personal-notes.txt").write_text("not part of the design")
    result = cli(tmp_path, "builder-init", key)
    pack = Path(result["builder_workspace"])
    lab_id = "ece329_solenoid_regression"
    assert (result["design_id"], result["lab_id"]) == (key, lab_id)
    assert cli(tmp_path, "show", key)["status_line"] == result["status_line"]
    premature = subprocess.run(
        [sys.executable, str(SKILL / "scripts/builder.py"), str(pack), "approve-gate",
         "--lab-id", lab_id, "--gate", "6", "--turn-id", "early", "--note", "test"],
        capture_output=True, encoding="utf-8",
    )
    assert premature.returncode and "Missing Gate 5B source selection" in premature.stderr
    inputs = pack / "LabSpecs" / lab_id / "design-input"
    assert Path(result["builder_inputs"]) == inputs
    assert result["builder_inputs_match_export"] is True
    if os.name == "nt":
        assert str(pack).startswith("\\\\?\\")
    assert 'language: "简体中文"' in (inputs.parent / "brief.yaml").read_text(encoding="utf-8")
    expected = {"design.pdf", "builder-gate1-input.pdf", "builder-gate1-input.json"}
    assert {f.name for f in inputs.iterdir()} == expected
    assert all((inputs / name).read_bytes() == (bundle / name).read_bytes() for name in expected)
    assert (pack / "UnityProject/LocalPackages/com.emvr.lab-common/package.json").is_file()
    assert not (pack / "KnowledgeBase/legacy-lab-specific-summaries").exists()
    assert cli(tmp_path, "show", key)["builder"]["current_gate"] == 0
    # An older running pack can predate the corrected export. Its inputs
    # are authoritative until the user chooses which edition to build.
    machine_copy.write_text('{"historical":"previous export"}', encoding="utf-8")
    frozen = inputs / machine_copy.name
    frozen.write_bytes(machine_copy.read_bytes())
    resumed = cli(tmp_path, "builder-init", key)
    assert (resumed["design_id"], resumed["lab_id"]) == (key, lab_id)
    assert resumed["builder_workspace"] == str(pack)
    assert resumed["builder_inputs_match_export"] is False
    assert frozen.read_bytes() == machine_copy.read_bytes()


    # Simulate an external labflow approval in this isolated test project.
    # Only an HTTP read follows it; the agent does not run show or write a snapshot.
    with page(tmp_path, key) as opened:
        url = opened["url"]
        published = tmp_path / "public/data" / (key + ".json")
        old_view = json.loads(published.read_text(encoding="utf-8"))
        old_view["check"].pop("details")
        old_view["flow"][0].pop("steps")
        published.write_text(json.dumps(old_view), encoding="utf-8")
        restored = get(url, f"data/{key}.json")
        assert len(restored["flow"][0]["steps"]) == 7
        assert "feasibility" in restored["check"]["details"]
        assert restored["builder"]["current_gate"] == 0
        state_file = pack / "LabSpecs" / lab_id / "workflow_state.json"
        working = json.loads(state_file.read_text(encoding="utf-8"))
        # Approvals from the retired Gate 6 and 8 definitions are insufficient
        # for user acceptance and handbooks in the current Builder.
        working["gate_approvals"] = {str(n): {"approved": True} for n in (0, 6, 8)}
        state_file.write_text(json.dumps(working), encoding="utf-8")
        progress = get(url, f"data/{key}.json")["builder"]
        assert progress["current_gate"] == 1 and progress["approved_gates"] == [0]
        saved = json.loads((tmp_path / "public/data" / (key + ".json")).read_text(encoding="utf-8"))
        assert saved["builder"] == progress
        # Interrupted handoff and stale snapshots must reconcile against the
        # current design fingerprint, even without another CLI show.
        path = tmp_path / "public/data" / (key + ".json")
        saved["builder"] = None
        path.write_text(json.dumps(saved), encoding="utf-8")
        assert get(url, f"data/{key}.json")["builder"] == progress
        marker = tmp_path / "private/runs" / key / "active.json"
        original = marker.read_bytes()
        marker.unlink()
        assert get(url, f"data/{key}.json")["builder"] is None
        marker.write_bytes(original)
        assert get(url, f"data/{key}.json")["builder"] == progress
        project = pack / "UnityProject"
        assert (project / "Assets/EmvrWorkflowPreview/Editor/EmvrSceneLayoutPreview.cs").is_file()
        scene = f"Assets/Scenes/{lab_id}.unity"
        asset = project / scene
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.touch()
        snapshot = project / "Library/EMVRLayout" / (scene + ".saved.json")
        snapshot.parent.mkdir(parents=True)
        geometry = b"mesh payload"
        digest = hashlib.sha256(geometry).hexdigest()
        snapshot.with_suffix(".json.bin").write_bytes(geometry)
        snapshot.write_text(json.dumps({"scene": scene, "fileTicks": str(asset.stat().st_mtime_ns // 100 + 621355968000000000),
            "geometry": digest, "objects": [{"id": 42, "name": "Probe", "position": {"x": 3, "y": 2, "z": 1},
            "mesh": 0, "matrix": [1,0,0,0,0,1,0,0,0,0,1,0,3,2,1,1], "colors": ["#ffffff"]}]}))
        layout = get(url, f"data/{key}.json")["layout"]
        assert layout["objects"][0]["position"] == [3, 2, 1]
        assert layout["geometry"] == digest
        with build_opener(ProxyHandler({})).open(urljoin(url, f"data/{key}.json?geometry={digest}")) as response:
            assert response.read() == geometry
    with page(tmp_path, "--builder-workspace", str(pack), "--lab-id", lab_id) as standalone:
        value = get(standalone["url"], "_session/" + standalone["viewer_session"])
        assert value["standalone"] is True and value["builder"]["current_gate"] == 1
        assert "workspace" not in value and "design_id" not in value
        assert value["layout"] == layout
        # Simulate a partial restore. The standalone page must not revert to "waiting for a workspace".
        record = pack / "LabSpecs" / lab_id / "workflow_state.json"
        saved_record = record.with_suffix(".backup")
        record.rename(saved_record)
        assert get(standalone["url"], "_session/" + standalone["viewer_session"])["builder"]["stage"] == "workspace_missing"
        assert cli(tmp_path, "show", key)["builder"]["stage"] == "workspace_missing"
        assert "gate record is missing" in cli(tmp_path, "builder-init", key, "--rebuild-missing", ok=False)
        saved_record.rename(record)

    # A removed build does not remove its local handoff or the saved design.
    pack.rename(pack.with_name("saved-run-backup"))
    assert cli(tmp_path, "show", key)["builder"]["stage"] == "workspace_missing"
    assert "--rebuild-missing" in cli(tmp_path, "builder-init", key, ok=False)
    found = cli(tmp_path, "find-handoff", key, "--revision", str(exported["revision"]))
    assert any(Path(c["folder"]).samefile(corrected) for c in found["candidates"])
    assert not any(Path(c["folder"]).samefile(bundle) for c in found["candidates"])
    incomplete = corrected.with_name(f"{exported['revision']}-interrupted-export")
    shutil.copytree(corrected, incomplete)
    (incomplete / "builder-gate1-input.pdf").write_bytes(b"")
    assert cli(tmp_path, "find-handoff", key, "--revision", str(exported["revision"])) == found
    assert not cli(tmp_path, "find-handoff", key, "--revision", "999999")["candidates"]
    assert not pack.exists()
    rebuilt = cli(tmp_path, "builder-init", key, "--rebuild-missing")
    assert Path(rebuilt["builder_workspace"]).samefile(pack)
    assert cli(tmp_path, "show", key)["builder"]["current_gate"] == 0


def test_viewer_upgrades_old_snapshot_once_even_when_user_quotes_old_wording():
    sys.path.insert(0, str(SKILL / "scripts"))
    from viewer import snapshot_is_current
    from workspace import SNAPSHOT_VERSION
    view = {"revision": 4, "check": {"details": {}},
            "notes": [{"value": "我的笔记：移动到选定观察位置并记录当前读数或场线形态"}]}
    assert not snapshot_is_current(4, view)
    view["check"]["snapshot_version"] = SNAPSHOT_VERSION
    assert snapshot_is_current(4, view)


def test_viewer_ignores_reused_port_with_non_viewer_json(monkeypatch):
    import io
    from unittest.mock import Mock
    sys.path.insert(0, str(SKILL / "scripts"))
    import viewer
    opener = Mock()
    opener.open.return_value = io.BytesIO(b"[]")
    monkeypatch.setattr(viewer, "build_opener", lambda *_: opener)
    assert viewer.running_url({"instance": "previous-worker", "port": 12345}) is None


def test_published_builder_snapshot_survives_without_its_private_session(tmp_path):
    sys.path.insert(0, str(SKILL / "scripts"))
    from viewer import live_design
    state, web = tmp_path / "private", tmp_path / "public"
    published = web / "data/example.json"
    published.parent.mkdir(parents=True)
    view = {"revision": 4, "builder_source_fingerprint": "approved-design",
            "builder": {"current_gate": 5}, "check": {"details": {}, "builder_ready": True}}
    original = json.dumps(view).encode()
    published.write_bytes(original)
    for with_database in (False, True):
        if with_database:
            SQLiteSessionStore(state / "design.sqlite3")
        assert live_design(state, web, "example") == view
        assert published.read_bytes() == original


def test_open_first_and_bind_only_this_design(tmp_path):
    sys.path.insert(0, str(SKILL / "scripts"))
    from viewer import instance_file
    marker = instance_file(tmp_path / "private", (tmp_path / "public").resolve())
    marker.parent.mkdir(parents=True)
    marker.write_text("{", encoding="utf-8")
    with page(tmp_path, "--new") as opened:
        url, token = opened["url"], opened["viewer_session"]
        assert get(url, "_session/" + token) == {"design_id": None}
        # Upgrade a live previous-protocol registration without invalidating
        # the URL that the host has already opened.
        marker = next((tmp_path / "private/viewer").glob("*.json"))
        info = json.loads(marker.read_text(encoding="utf-8"))
        info.pop("protocol")
        # A user's pre-3D web directory can still serve the bundled preview.
        (tmp_path / "public/scene-preview.js").unlink()
        temp = marker.with_suffix(".new")
        temp.write_text(json.dumps(info), encoding="utf-8")
        temp.replace(marker)
        same_server = json.loads(viewer_command(tmp_path, "open", "--url-only").stdout)
        assert urlsplit(same_server["url"]).netloc == urlsplit(url).netloc
        assert get(url, "_instance")["instance"] != info["instance"]
        with build_opener(ProxyHandler({})).open(urljoin(url, "scene-preview.js")) as response:
            assert response.read() == (ROOT / "web/scene-preview.js").read_bytes()
        assert len(get(url, "stages.json")["design"]) == 7
        key = cli(tmp_path, "create", "线圈电流和磁场", "--viewer-session", token)["design_id"]
        assert get(url, "_session/" + token) == {"design_id": key}
        assert cli(tmp_path, "create", "重试", "--viewer-session", token)["design_id"] == key
        # A process can commit a turn to SQLite and exit before publishing its snapshot.
        published = tmp_path / "public/data" / (key + ".json")
        old_snapshot = published.read_bytes()
        turn = cli(tmp_path, "turn", key, "--message", "请解释当前的公式")
        published.write_bytes(old_snapshot)
        assert get(url, f"data/{key}.json")["revision"] == turn["revision"]
        assert json.loads(published.read_bytes())["revision"] == turn["revision"]
        other = cli(tmp_path, "create", "传播方向")["design_id"]
        assert other != key and get(url, "data/latest.json")["design_id"] == other
        assert get(url, "_session/" + token) == {"design_id": key}


def test_unity_tarball_matches_builder_package():
    pack = ROOT / "reusable-code/EMVR_Blind_BuilderPack/UnityProject"
    source = pack / "LocalPackages/com.emvr.lab-common"
    manifest = json.loads((source / "package.json").read_text(encoding="utf-8"))
    unity = json.loads((pack / "Packages/manifest.json").read_text(encoding="utf-8"))
    assert unity["dependencies"][manifest["name"]] == "file:../LocalPackages/" + manifest["name"]
    file = ROOT / "unity-package" / (manifest["name"] + "-" + manifest["version"] + ".tgz")
    with tarfile.open(file) as archive:
        expected = {"package/" + p.relative_to(source).as_posix(): p for p in source.rglob("*") if p.is_file()}
        assert set(archive.getnames()) == set(expected)
        assert all(archive.extractfile(name).read() == path.read_bytes() for name, path in expected.items())


def test_knowledge_inputs():
    catalog = json.loads((ROOT / "knowledge/catalog.json").read_text(encoding="utf-8"))
    for name, rel in catalog.items():
        if name != "base":
            assert not Path(rel).is_absolute() and (ROOT / rel).is_dir()
    course = ROOT / catalog["course"]
    lecture = json.loads((course / "source_manifest.json").read_text(encoding="utf-8"))
    books = json.loads((course / "supplemental_sources.json").read_text(encoding="utf-8"))["sources"]
    for filename, expected in [(lecture["source_filename"], lecture["sha256"]),
                               *((book["local_filename"], book["sha256"]) for book in books)]:
        with (ROOT / catalog["sources"] / filename).open("rb") as source:
            assert hashlib.file_digest(source, "sha256").hexdigest() == expected.lower()


def test_new_library_documents_are_immediately_searchable(tmp_path):
    sys.path.insert(0, str(SKILL / "scripts"))
    from library import copy_builder_references, search
    catalog = json.loads((ROOT / "knowledge/catalog.json").read_text(encoding="utf-8"))
    for key, rel in catalog.items():
        if key != "base":
            (tmp_path / rel).mkdir(parents=True, exist_ok=True)
    (tmp_path / "knowledge/catalog.json").write_text(json.dumps(catalog))
    for area in ("design", "builder", "shared"):
        (tmp_path / catalog[area + "_additions"] / "notes.md").write_text("isolated-needle", encoding="utf-8")
    (tmp_path / catalog["updates"] / "review.md").write_text("isolated-needle", encoding="utf-8")
    archive_doc = catalog["builder_archive"] + "/reusable.md"
    (tmp_path / archive_doc).write_text("conditional-category-b", encoding="utf-8")
    for scope in ("builder", "all"):
        assert search(tmp_path, "conditional-category-b", scope)["documents"][0]["path"] == archive_doc
    assert not search(tmp_path, "conditional-category-b", "design")["documents"]
    for scope in ("design", "builder"):
        found = search(tmp_path, "isolated-needle", scope)["documents"]
        assert {row["path"] for row in found} == {
            catalog["updates"] + "/review.md", catalog[scope + "_additions"] + "/notes.md", catalog["shared_additions"] + "/notes.md"}
    update = tmp_path / catalog["updates"] / "review.md"
    update.write_text("solenoid overview\nsolenoid calibration", encoding="utf-8")
    for index in range(31):
        (tmp_path / catalog["builder_lessons"] / f"note{index}.md").write_text("solenoid")
    hits = search(tmp_path, "solenoid calibration", "builder")["documents"]
    assert hits[0] == {"path": catalog["updates"] + "/review.md", "line": 2, "excerpt": "solenoid calibration"}
    pack = tmp_path / "isolated-run"
    copy_builder_references(tmp_path, pack)
    assert {path.relative_to(pack).as_posix() for path in pack.rglob("*.md")} == {
        "KnowledgeBase/extensions/newknowledge/review.md", "KnowledgeBase/extensions/shared/notes.md", "KnowledgeBase/extensions/builder/notes.md"}

def test_archived_guided_design_opens_from_store_without_builder_approval(tmp_path):
    key = "historic_guided"
    store = SQLiteSessionStore(tmp_path / "private/design.sqlite3")
    session = DesignSession(key, InteractionState.GUIDED_DESIGN, status=WorkflowStatus.COMPLETE,
                            current_stage_index=len(Stage)-1, revision=5,
                            design_context={"idea": {"original": "磁场测量"}, "synthesis": {"student_summary": "比较磁场方向"}})
    session.stage_outputs[session.current_stage.value] = {"revision": 3, "assistant_message": "已记录总结"}
    store.save(session)
    with page(tmp_path, key) as opened:
        view = get(opened["url"], f"data/{key}.json")
        assert view["check"]["archived"] and not view["check"]["builder_ready"]
        assert view["notes"][-1]["value"] == "比较磁场方向" and view["builder"] is None
    shown = cli(tmp_path, "show", key)
    assert shown["revision"] == 5 and shown["workflow_status"] == "complete"
    assert "student_task" not in shown and "assistant_message" not in shown
    for command in ("export", "builder-init"):
        assert "历史设计已归档" in cli(tmp_path, command, key, ok=False)
    assert store.get(key).interaction_state is InteractionState.GUIDED_DESIGN


def test_host_feedback_reaches_later_turn(tmp_path):
    from tests.test_feedback_pipeline import candidate, review_note
    key = cli(tmp_path, "create", "磁场")["design_id"]
    args = ("feedback", key, "--submit")
    ticket = cli(tmp_path, *args, stdin={"request_id": "example-feedback", "message": "已经回答"})
    process = ("feedback-process", "--ticket", ticket["id"])
    assert cli(tmp_path, *process)["ticket"]["id"] == ticket["id"]
    proposal = candidate(keywords=["磁场"])
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps({"ticket_id": ticket["id"], "candidate": proposal}))
    analyzed = cli(tmp_path, *process, "--candidate", str(path))
    assert analyzed["status"] == "candidate"
    identity = analyzed["experience"]["id"]
    from ece329_workflow.experience import ExperienceStore
    store = ExperienceStore(tmp_path / "private/design.sqlite3")
    version = store.experiences(experience_id=identity)[0]["version"]
    cli(tmp_path, "experience-review", identity, stdin={
        "decision":"approve", "version":version, "note":review_note(proposal)})
    later = cli(tmp_path, "turn", key, "--message", "磁场")
    assert any(rule["id"] == "EXP-" + identity for rule in later["experience_rules"])
    assert "Gate 8" in cli(tmp_path, "retrospective", key, "--notes", str(path), ok=False)


def test_export_host_language_and_switch(tmp_path):
    import re
    _, session = completed_magnetic_engine()
    session._store_snapshot = None
    session.model_context["response_language"] = "en"
    SQLiteSessionStore(tmp_path / "private/design.sqlite3").save(session)
    key = session.design_id
    request = cli(tmp_path, "export", key)
    assert request["language"] == "en" and request["translation_required"]
    path = tmp_path / "en.json"
    # Transport double: keep numeric, code and formula references intact.
    path.write_text(json.dumps({s: re.sub(r"[\u3400-\u9fff]+", "sample", s) for s in request["translations"]}))
    done = cli(tmp_path, "export", key, "--translations", str(path))
    assert (Path(done["artifacts"]) / "design.pdf").read_bytes().startswith(b"%PDF")
    contract = Path(done["artifacts"]) / "builder-gate1-input.json"
    approved = contract.read_bytes()
    contract.unlink()
    assert cli(tmp_path, "export", key)["artifacts"] == done["artifacts"]
    assert contract.read_bytes() == approved
    zh = cli(tmp_path, "export", key, "--language", "zh")
    if zh.get("translation_required"):
        path.write_text(json.dumps({s: "译文 " + s for s in zh["translations"]}))
        zh = cli(tmp_path, "export", key, "--language", "zh", "--translations", str(path))
    assert Path(done["artifacts"]) != Path(zh["artifacts"])
    assert (Path(zh["artifacts"]) / "builder-gate1-input.pdf").read_bytes().startswith(b"%PDF")


def test_gate5b_archive_bound_to_acceptance(tmp_path, monkeypatch):
    sys.path.insert(0, str(SKILL / "scripts"))
    import code_archive
    pack = tmp_path / "pack"
    owned = pack / "UnityProject/Assets/Scripts/Lab.cs"
    owned.parent.mkdir(parents=True)
    owned.write_text("class Scaffold {}")
    status = {"current_gate":5,"accepted":False,"approved_gates":[],
              "evidence":{"gate5_foundation":"passed","compile_content_digest":"a"*64}}
    monkeypatch.setattr(code_archive, "labflow", lambda *args: json.dumps(status))
    out = tmp_path / "newcode"
    def run(action, *files):
        return code_archive.archive(pack, "course_lab", action, files, out)
    run("begin")
    import pytest
    with pytest.raises(ValueError):
        run("capture", "Scripts/Lab.cs")
    owned.write_text("class Lab {}")
    (owned.parent / "Plot.cs").write_text("class Plot {}")
    selection = run("capture", r"Scripts\Lab.cs")
    assert selection == {"selected": ["Scripts/Lab.cs"], "unselected_changes": ["Scripts/Plot.cs"]}
    with pytest.raises(ValueError):
        run("publish")
    status.update(current_gate=8, accepted=True, approved_gates=[0,1,2,3,4,5,6])
    rename = Path.rename
    attempts = []

    def briefly_locked(source, destination):
        attempts.append(destination)
        if len(attempts) == 1:
            error = PermissionError("accepted code directory temporarily locked")
            error.winerror = 32
            raise error
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", briefly_locked)
    result = run("publish")
    assert len(attempts) == 2
    assert (Path(result["archive"]) / "Scripts/Lab.cs").read_text() == "class Lab {}"
    copy = Path(result["archive"]) / "Scripts/Lab.cs"
    copy.unlink()
    assert run("publish") == result
    assert copy.read_bytes() == owned.read_bytes()
    copy.write_text("Archive with a different recorded source")
    with pytest.raises(ValueError, match="Archive conflict"):
        run("publish")
    assert copy.read_text() == "Archive with a different recorded source"
    status.clear()
    status.update(migration_required=True, current_gate=None)
    with pytest.raises(ValueError, match="legacy"):
        run("publish")

def test_legacy_retrospective_replay_preserves_searchable_gate8_archive(tmp_path, monkeypatch):
    sys.path.insert(0, str(SKILL / "scripts"))
    import workflow
    import pytest
    engine, session = completed_magnetic_engine()
    session._store_snapshot = None
    SQLiteSessionStore(tmp_path / "private/design.sqlite3").save(session)
    shutil.copytree(ROOT / "knowledge", tmp_path / "knowledge", ignore=shutil.ignore_patterns("*.pdf"))
    monkeypatch.setattr(workflow, "ROOT", tmp_path)
    def completed_builder(state, key, fingerprint):
        return {"workflow_complete": True, "accepted": True, "source_fingerprint": fingerprint,
                "knowledge_update": f"knowledge/newknowledge/{key}/{fingerprint}.md"}
    monkeypatch.setattr(workflow, "active_builder", completed_builder)
    notes = tmp_path / "notes.md"
    notes.write_text("Design: solenoid. Builder: verify recap-current.", encoding="utf-8")
    design = engine.get_design(session.design_id)
    record = completed_builder(None, session.design_id, workflow.builder_fingerprint(design))["knowledge_update"]
    archived = tmp_path / record
    archived.parent.mkdir(parents=True)
    archived.write_bytes(notes.read_bytes())
    monkeypatch.setattr(sys, "argv", ["workflow", "--state-dir", str(tmp_path / "private"),
        "--web-dir", str(tmp_path / "web"), "retrospective", session.design_id, "--notes", str(notes)])
    assert workflow.main()["knowledge_update"] == record
    # A pending upload does not undo the archived retrospective.
    monkeypatch.setattr(workflow, "active_builder", lambda *args: {
        **completed_builder(*args), "workflow_complete": False, "upload_pending": True})
    assert workflow.main()["knowledge_update"] == record
    notes.write_text("Different retrospective", encoding="utf-8")
    with pytest.raises(ValueError, match="already archived"):
        workflow.main()
    assert "recap-current" in archived.read_text(encoding="utf-8")
    for scope in ("design", "builder"):
        assert workflow.search(tmp_path, "recap-current", scope)["documents"][0]["path"] == record
