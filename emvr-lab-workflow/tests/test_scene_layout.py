import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scene_layout import scene_layout


def test_layout_follows_registered_scene_and_prefers_current_editor_state(tmp_path):
    scene = "Assets/Scenes/MyLab.unity"
    state = tmp_path / "LabSpecs/demo/workflow_state.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"scene": scene}))
    project = tmp_path / "UnityProject"
    asset = project / scene
    asset.parent.mkdir(parents=True)
    asset.touch()
    assert scene_layout(tmp_path, "demo") is None
    cache = project / "Library/EMVRLayout"
    saved = cache / (scene + ".saved.json")
    live = cache / (scene + ".live.json")
    saved.parent.mkdir(parents=True)
    blob = b"saved scene mesh"
    digest = hashlib.sha256(blob).hexdigest()
    data = {"scene": scene, "fileTicks": str(asset.stat().st_mtime_ns // 100 + 621355968000000000),
            "objects": [{"id": 2, "name": "Probe", "position": {"x": 1, "y": 2, "z": 3},
                         "matrix": [1,0,0,0,0,1,0,0,0,0,1,0,1,2,3,1], "mesh": 0, "colors": []}]}
    saved.write_text(json.dumps(data))
    assert scene_layout(tmp_path, "demo") is None  # coordinate-only snapshots
    data["geometry"] = digest
    saved.with_suffix(".json.bin").write_bytes(blob)
    live.with_suffix(".json.bin").write_bytes(blob)
    saved.write_text(json.dumps(data))
    assert scene_layout(tmp_path, "demo")["objects"][0]["position"] == [1, 2, 3]
    assert scene_layout(tmp_path, "demo", digest) == blob
    assert scene_layout(tmp_path, "demo", "0"*64) is None
    live.write_text(json.dumps(data))
    assert scene_layout(tmp_path, "demo")["source"] == "live"
    live.write_text("{")
    assert scene_layout(tmp_path, "demo")["source"] == "saved"
    live.write_text(json.dumps({**data, "geometry": None}))
    assert scene_layout(tmp_path, "demo")["source"] == "saved"
    live.write_text(json.dumps({**data, "objects": []}))
    assert scene_layout(tmp_path, "demo") is None
    os.utime(live, (1, 1))
    assert scene_layout(tmp_path, "demo")["source"] == "saved"
    os.utime(asset, (2, 2))
    assert scene_layout(tmp_path, "demo") is None
    state.write_text(json.dumps({"scene": "Assets/Scenes/../Other.unity"}))
    assert scene_layout(tmp_path, "demo") is None
