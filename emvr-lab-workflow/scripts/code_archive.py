"""Record Gate 5B source changes and publish the accepted copies after Gate 6."""
import argparse
import filecmp
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from workspace import ROOT, approve_user_gate, dump, labflow, lock, native_path, publish_directory, read_builder_status, valid_id, write_json


SOURCE_TYPES = {".cs", ".shader", ".shadergraph", ".shadersubgraph", ".compute", ".hlsl", ".cginc", ".asmdef", ".asmref"}


def sources(pack):
    assets = pack / "UnityProject/Assets"
    result = {}
    for path in assets.rglob("*"):
        if path.suffix.lower() not in SOURCE_TYPES or not path.is_file():
            continue
        rel = path.relative_to(assets)
        if "Gate5Foundation" in rel.parts or not path.resolve().is_relative_to(assets.resolve()):
            continue
        result[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def archive(pack, lab, action, files=(), destination=ROOT / "reusable-code/newcode", approval_note=None, turn_id=None):
    pack = native_path(pack.resolve())
    evidence = pack / "BuildEvidence" / valid_id(lab) / "gate5b-archive"
    with lock(evidence / "record.lock"):
        status = json.loads(labflow(pack, "status", "--lab-id", lab))
        baseline = evidence / "before.json"
        selection = evidence / "selection.json"
        if status.get("migration_required"):
            raise ValueError("Migrate the legacy Builder state and re-approve the gates before archiving.")
        if action == "begin":
            if baseline.exists():
                return {"baseline_recorded": True}
            if status["current_gate"] != 5 or status["evidence"].get("gate5_foundation") != "passed":
                raise ValueError("Record the baseline after Gate 5A passes and before editing the domain slice.")
            write_json(baseline, sources(pack))
            return {"baseline_recorded": True}
        if action == "capture":
            if status["current_gate"] != 5 or not baseline.exists():
                raise ValueError("Capture Gate 5B files during Gate 5 after recording the baseline.")
            before = json.loads(baseline.read_text(encoding="utf-8"))
            now = sources(pack)
            selected = sorted({Path(name.replace(chr(92), "/")).as_posix() for name in files})
            if not selected or any(path not in now or now[path] == before.get(path) for path in selected):
                raise ValueError("Select new or modified Gate 5B source files relative to UnityProject/Assets.")
            write_json(selection, selected)
            changed = {path for path, digest in now.items() if digest != before.get(path)}
            return {"selected": selected, "unselected_changes": sorted(changed.difference(selected))}
        if not selection.is_file():
            raise ValueError("Missing Gate 5B source selection.")
        selected = json.loads(selection.read_text(encoding="utf-8"))
        assets = (pack / "UnityProject/Assets").resolve()
        inputs = []
        for name in selected:
            source = (assets / name).resolve()
            if (not source.is_relative_to(assets) or source.suffix.lower() not in SOURCE_TYPES
                    or "Gate5Foundation" in source.parts or not source.is_file()):
                raise ValueError(f"Missing or invalid Gate 5B source: {name}")
            inputs.append(source)
            meta = source.with_suffix(source.suffix + ".meta")
            if meta.is_file() and meta.resolve().is_relative_to(assets):
                inputs.append(meta)
        if not inputs:
            raise ValueError("The Gate 5B source selection is empty.")
        if approval_note and status.get("current_gate") == 6:
            approve_user_gate(pack, lab, 6, approval_note, turn_id)
            status = json.loads(labflow(pack, "status", "--lab-id", lab))
        approved = status.get("approved_gates")
        past_gate6 = 6 in approved if approved is not None else (status.get("current_gate") == 8 or status.get("workflow_complete"))
        if not status.get("accepted") or not past_gate6:
            raise ValueError("Gate 6 user acceptance must be current before archiving code.")
        fingerprint = status["evidence"].get("compile_content_digest")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(c not in "0123456789abcdef" for c in fingerprint.lower()):
            raise ValueError("Invalid acceptance digest.")
        target = native_path(destination.resolve()) / lab / fingerprint
        target.parent.mkdir(parents=True, exist_ok=True)
        # Different workspaces can publish the same accepted revision.
        with lock(target.with_suffix(".lock")), tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            bundle = Path(tmp) / "code"
            missing = []
            for source in inputs:
                relative = source.relative_to(assets)
                existing = target / relative
                if existing.is_file() and filecmp.cmp(source, existing, shallow=False):
                    continue
                output = bundle / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, output)
                missing.append(relative)
            current = json.loads(labflow(pack, "status", "--lab-id", lab))
            if not current.get("accepted") or current.get("evidence", {}).get("compile_content_digest") != fingerprint:
                raise ValueError("Acceptance changed while copying. Recheck the accepted source.")
            if not target.exists():
                publish_directory(bundle, target)
            else:
                for relative in missing:
                    output = target / relative
                    output.parent.mkdir(parents=True, exist_ok=True)
                    (bundle / relative).replace(output)
        return {"archive": str(target), "files": selected}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["begin", "capture", "publish"])
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--lab-id", required=True, type=valid_id)
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--approval-note", help="Record explicit user acceptance before publishing")
    parser.add_argument("--turn-id", help="ID of the user message approving Gate 6")
    args = parser.parse_args()
    if args.approval_note and args.action != "publish":
        parser.error("--approval-note is only used when publishing Gate 6")
    try:
        result = archive(args.workspace, args.lab_id, args.action, args.file, approval_note=args.approval_note, turn_id=args.turn_id)
        result["status_line"] = read_builder_status(args.workspace, args.lab_id)["status_line"]
        print(dump(result))
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
