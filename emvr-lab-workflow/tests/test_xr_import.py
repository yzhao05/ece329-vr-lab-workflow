import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import xr_import
from workspace import BASE


@pytest.fixture
def imported(tmp_path, monkeypatch):
    lab = "xr_test"
    source = tmp_path / "ApprovedAssets" / xr_import.XR_SETUP
    dest = tmp_path / "UnityProject/Assets/Generated" / lab / "ApprovedDependencies" / xr_import.XR_SETUP
    original = BASE / "ApprovedAssets" / xr_import.XR_SETUP
    for path in (source, dest):
        path.parent.mkdir(parents=True)
        shutil.copyfile(original, path)
        shutil.copyfile(original.with_suffix(".prefab.meta"), path.with_suffix(".prefab.meta"))
    receipt = tmp_path / "BuildEvidence" / lab / "approved-asset-imports/XR Interaction Setup-fea27b3063.json"
    receipt.parent.mkdir(parents=True)
    record = {"source": source.relative_to(tmp_path).as_posix(), "destination": dest.relative_to(tmp_path).as_posix(),
              "sha256": hashlib.sha256(source.read_bytes()).hexdigest().upper(),
              "meta_sha256": hashlib.sha256(source.with_suffix(".prefab.meta").read_bytes()).hexdigest().upper()}
    receipt.write_text(json.dumps({"lab_id": lab, "dry_run": False, "approved_source": record["source"], "assets": [record]}))
    monkeypatch.setattr(xr_import, "labflow", lambda *_: '{"current_gate":5}')
    changed = source.read_bytes().replace(
        b"m_PointAction: {fileID: 2869410428622933342, guid: c348712bda248c246b8c49b3db54643f,\n    type: 3}",
        b"m_PointAction: {fileID: 0}",
    )
    assert changed != source.read_bytes()
    dest.write_bytes(changed)
    return tmp_path, lab, dest, source, receipt


def test_restores_exact_bytes_and_keeps_first_backup(imported):
    pack, lab, dest, source, _ = imported
    changed = dest.read_bytes()
    result = xr_import.repair_xr_import(pack, lab)
    assert result["status"] == "restored"
    assert (pack / result["backup"]).read_bytes() == changed
    assert dest.read_bytes() == source.read_bytes()
    assert (pack / xr_import.GUARD / "Editor/EmvrXrImportSaveGuard.cs").is_file()
    assert xr_import.repair_xr_import(pack, lab)["status"] == "already_matches"
    assert (pack / result["backup"]).read_bytes() == changed


@pytest.mark.parametrize("case", ["source", "source_meta", "copy_meta", "receipt", "other_field", "gate", "gate5b", "unity_open"])
def test_refuses_unverified_recovery(imported, case, monkeypatch):
    pack, lab, dest, source, receipt = imported
    if case == "source":
        source.write_bytes(dest.read_bytes())
    elif case == "source_meta":
        source.with_suffix(".prefab.meta").write_bytes(b"other GUID")
    elif case == "copy_meta":
        dest.with_suffix(".prefab.meta").write_bytes(b"other GUID")
    elif case == "receipt":
        item = json.loads(receipt.read_text())
        item["assets"][0]["destination"] = "UnityProject/Assets/unrelated.prefab"
        receipt.write_text(json.dumps(item))
    elif case == "other_field":
        dest.write_bytes(dest.read_bytes().replace(b"m_EnableXRInput: 1", b"m_EnableXRInput: 0"))
    elif case == "gate":
        monkeypatch.setattr(xr_import, "labflow", lambda *_: '{"current_gate":6}')
    elif case == "gate5b":
        monkeypatch.setattr(xr_import, "labflow", lambda *_: '{"current_gate":5,"evidence":{"gate5_foundation":"passed"}}')
    elif case == "unity_open":
        marker = pack / "UnityProject/Temp/UnityLockfile"
        marker.parent.mkdir()
        marker.touch()
    before = dest.read_bytes()
    with pytest.raises(ValueError):
        xr_import.repair_xr_import(pack, lab)
    assert dest.read_bytes() == before
    assert not (receipt.parent.parent / "xr-import-recovery").exists()
