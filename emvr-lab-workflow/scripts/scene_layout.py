"""Read only the Unity Editor layout belonging to a lab's registered scene."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import time

from workspace import native_path, valid_id, write_text


PREVIOUS_BRIDGES = {
    "a8cae74378620b6f01d8afb5c37bca785dcde3825e0c53739eefa37c6110d9d0",  # coordinate-only preview
    "6ab38f39d8eee265ea4b11978d54f23800b5ecf2d142ac9b7c294d71ddfecd7a",  # first mesh preview
    "ca0b0925290cb1269c831711645b9fcf91ff741e091b84dc427b3508cf6dd1f2",  # mesh preview with dynamic mesh caching
}


def install_layout_bridge(project):
    source = Path(__file__).with_name("EmvrSceneLayoutPreview.cs")
    target = native_path(project) / "Assets/EmvrWorkflowPreview/Editor" / source.name
    script = source.read_text(encoding="utf-8")
    if target.exists():
        existing = target.read_bytes().replace(b"\r\n", b"\n")
        if existing == script.encode("utf-8"):
            return
        if hashlib.sha256(existing).hexdigest() not in PREVIOUS_BRIDGES:
            raise ValueError(f"Existing scene preview script differs from this package: {target}")
    write_text(target, script)


def _snapshot_manifest(cache, relative, source, ticks):
    snapshot = (cache / (relative.as_posix() + f".{source}.json")).resolve()
    if not snapshot.is_relative_to(cache):
        return None
    try:
        if source == "live" and time.time() - snapshot.stat().st_mtime > 10:
            return None
        data = json.loads(snapshot.read_text(encoding="utf-8-sig"))
        if data["scene"] == relative.as_posix() and int(data["fileTicks"]) == ticks:
            return data
    except (OSError, ValueError, KeyError, TypeError):
        # The editor may have closed or replaced its live manifest during this poll.
        pass
    return None


def scene_layout(pack, lab, geometry=None):
    pack = native_path(pack)
    project = pack / "UnityProject"
    try:
        state = json.loads((pack / "LabSpecs" / valid_id(lab) / "workflow_state.json").read_text(encoding="utf-8"))
        name = state.get("scene", f"Assets/Scenes/{lab}.unity").replace("\\", "/")
        relative = PurePosixPath(name)
        if relative.parts[:2] != ("Assets", "Scenes") or relative.suffix != ".unity" or ".." in relative.parts or ":" in name:
            return None
        scene = (project / relative).resolve()
        if not scene.is_relative_to((project / "Assets/Scenes").resolve()):
            return None
        # .NET ticks start in year 1 and use 100 ns units.
        ticks = scene.stat().st_mtime_ns // 100 + 621355968000000000
        cache = (project / "Library/EMVRLayout").resolve()
        for source in ("live", "saved"):
            data = _snapshot_manifest(cache, relative, source, ticks)
            if data is None:
                continue
            if data.get("objects") == []:
                return None  # A genuinely empty live scene supersedes the saved scene.
            digest = data.get("geometry")
            if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
                continue
            binary = (cache / (relative.as_posix() + f".{source}.json.bin")).resolve()
            if not binary.is_relative_to(cache) or not binary.is_file():
                continue
            if geometry is not None:
                if geometry != digest:
                    return None
                content = binary.read_bytes()
                # Unity can publish a new mesh between reading the manifest and the file.
                return content if hashlib.sha256(content).hexdigest() == digest else None
            items = []
            for item in data["objects"]:
                position = [item["position"][axis] for axis in "xyz"]
                matrix = item["matrix"]
                if len(matrix) == 16 and all(math.isfinite(n) for n in position + matrix):
                    items.append({"id": item["id"], "name": item["name"], "position": position,
                                  "mesh": item["mesh"], "matrix": matrix, "colors": item["colors"]})
            return {"scene": relative.stem, "source": source, "geometry": digest, "objects": items} if items else None
    except (OSError, ValueError, AttributeError, KeyError, TypeError, OverflowError):
        return None
    return None
