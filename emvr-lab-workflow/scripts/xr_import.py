"""Protect the Gate 5 XR import and restore a previously rewritten input reference."""
import hashlib
import json
from pathlib import Path
import re

from workspace import BASE, labflow, lock, native_path, write_bytes, write_text


XR_SETUP = Path("XRInteractionToolkitSamples/Starter Assets/Prefabs/XR Interaction Setup.prefab")
GUARD = Path("UnityProject/Assets/EmvrImportProtection")
# Ignore reference values only to classify the diff before restoring the approved bytes.
# A changed reference is never accepted as evidence for a gate.
ACTION_REFERENCE = re.compile(
    rb"^(  m_(?:Point|LeftClick|MiddleClick|RightClick|ScrollWheel|Navigate|Submit|Cancel)Action: "
    rb"|  m_ActionAssets:\n  - )\{fileID: -?\d+(?:, guid: [\da-fA-F]{32},(?: |\n    )type: \d+)?\}",
    re.MULTILINE,
)


def checked(path, pack):
    if not path.is_relative_to(pack) or path.resolve() != path:
        raise ValueError(f"Unexpected link in XR import path: {path}")
    return path


def install_guard(pack):
    script = GUARD / "Editor/EmvrXrImportSaveGuard.cs"
    paths = (GUARD.with_suffix(".meta"), GUARD / "Editor.meta", script.with_suffix(".cs.meta"), script)
    missing = {}
    for relative in paths:
        target = checked(pack / relative, pack)
        expected = (BASE / relative).read_text(encoding="utf-8")
        if target.exists():
            if target.read_text(encoding="utf-8") != expected:
                raise ValueError(f"Existing XR save guard differs from this package: {target}")
        else:
            missing[target] = expected
    for target, expected in missing.items():
        write_text(target, expected)


def repair_xr_import(pack, lab_id):
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", lab_id):
        raise ValueError("Expected a Builder lab_id.")
    pack = native_path(pack).resolve()
    status = json.loads(labflow(pack, "status", "--lab-id", lab_id))
    if status.get("current_gate") != 5 or status.get("evidence", {}).get("gate5_foundation") == "passed":
        raise ValueError("Restore the XR import only at Gate 5A, before recording its validation.")
    evidence = checked(pack / "BuildEvidence" / lab_id, pack)
    with lock(checked(evidence / "xr-import-repair.lock", pack)):
        if (pack / "UnityProject/Temp/UnityLockfile").exists():
            raise ValueError("Save the scene and close this Unity project before restoring the XR import.")
        source = checked(pack / "ApprovedAssets" / XR_SETUP, pack)
        dest = checked(pack / "UnityProject/Assets/Generated" / lab_id / "ApprovedDependencies" / XR_SETUP, pack)
        approved = (BASE / "ApprovedAssets" / XR_SETUP).read_bytes()
        approved_meta = (BASE / "ApprovedAssets" / XR_SETUP.with_suffix(".prefab.meta")).read_bytes()
        expected = {"source": source.relative_to(pack).as_posix(), "destination": dest.relative_to(pack).as_posix(),
                    "sha256": hashlib.sha256(approved).hexdigest().upper(),
                    "meta_sha256": hashlib.sha256(approved_meta).hexdigest().upper()}
        source_meta = checked(source.with_suffix(".prefab.meta"), pack)
        dest_meta = checked(dest.with_suffix(".prefab.meta"), pack)
        if source.read_bytes() != approved or source_meta.read_bytes() != approved_meta or dest_meta.read_bytes() != approved_meta:
            raise ValueError("XR approved source or .meta differs from the release. Maintainer review required.")
        key = hashlib.sha256(XR_SETUP.as_posix().encode()).hexdigest()[:10]
        manifest = checked(evidence / "approved-asset-imports" / f"{XR_SETUP.stem}-{key}.json", pack)
        record = json.loads(manifest.read_text(encoding="utf-8-sig"))
        if (record.get("dry_run") is not False or record.get("lab_id") != lab_id
                or record.get("approved_source") != expected["source"] or expected not in record.get("assets", [])):
            raise ValueError("XR import receipt does not match this lab and release. Maintainer review required.")
        before = dest.read_bytes()
        if before != approved and ACTION_REFERENCE.sub(rb"\1{}", before) != ACTION_REFERENCE.sub(rb"\1{}", approved):
            raise ValueError("XR prefab differs outside the supported input references. Keep the copy for maintainer review.")
        install_guard(pack)
        if before == approved:
            return {"status": "already_matches", "sha256": expected["sha256"]}
        backup = checked(evidence / "xr-import-recovery" / (hashlib.sha256(before).hexdigest() + ".prefab"), pack)
        if not backup.exists():
            write_bytes(backup, before)
        if backup.read_bytes() != before:
            raise ValueError(f"XR recovery backup verification failed: {backup}")
        if dest.read_bytes() != before:
            raise ValueError("XR prefab changed during recovery. Close Unity and retry.")
        write_bytes(dest, approved)
        if dest.read_bytes() != approved:
            raise ValueError("XR prefab verification after restore failed.")
        return {"status": "restored", "backup": backup.relative_to(pack).as_posix(), "sha256": expected["sha256"]}
