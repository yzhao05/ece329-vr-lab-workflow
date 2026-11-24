"""Use the run's Builder CLI, or obtain a short Unity Editor project path."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from scene_layout import install_layout_bridge

from workspace import BASE, DEFAULT_STATE, ROOT, SKILL, approve_user_gate, builder_command, builder_progress, dump, labflow, native_path, read_builder_status, unified_builder_status
from maintainer_upload import prepare_upload


def locate_pack(workspace, state):
    if native_path(workspace).is_dir():
        return workspace
    lab = str(workspace)
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", lab):
        raise ValueError(f"Builder workspace does not exist: {workspace}")
    roots = [state] if state is not None else [SKILL / "state", ROOT / "state"]
    matches = sorted({item.parents[2].resolve() for root in roots
                      for item in (native_path(root) / "builds").glob(f"*/{BASE.name}/LabSpecs/{lab}/workflow_state.json")})
    if len(matches) == 1:
        return matches[0]
    if matches:
        raise ValueError("Multiple workspaces match. Run unity-project with the intended workspace path:\n" +
                         "\n".join(map(str, matches)))
    raise ValueError(f"No saved Builder workspace for {lab}. Supply its workspace path or --state-dir.")


def unity_project(pack):
    project = pack / "UnityProject"
    if not native_path(project / "ProjectSettings/ProjectVersion.txt").is_file():
        raise ValueError("Expected a Builder workspace containing UnityProject/ProjectSettings/ProjectVersion.txt")
    install_layout_bridge(project)
    if os.name != "nt":
        return project
    import _winapi
    target = native_path(project.resolve(strict=True))
    if target.drive.upper().startswith("\\\\?\\UNC\\"):
        raise ValueError("A persistent Unity junction requires a local project. Move the workspace to a local disk first.")
    key = hashlib.sha256(os.path.normcase(str(target)).encode("utf-8")).hexdigest()[:16]
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise ValueError("LOCALAPPDATA is unavailable. Run unity-project in the Windows account used for Unity Hub.")
    alias = Path(local) / "EMVR" / key
    alias.parent.mkdir(parents=True, exist_ok=True)
    if not os.path.lexists(alias):
        # A failed CreateJunction can leave an empty directory. Only publish a
        # verified junction, and never replace a concurrently created entry.
        with tempfile.TemporaryDirectory(dir=alias.parent) as staging:
            link = Path(staging) / "project"
            _winapi.CreateJunction(str(target).removeprefix("\\\\?\\"), str(link))
            if not link.samefile(target):
                raise ValueError(f"Cannot verify Unity junction for {target}")
            try:
                link.rename(alias)
            except FileExistsError:
                pass
    if (getattr(alias.lstat(), "st_reparse_tag", None) != stat.IO_REPARSE_TAG_MOUNT_POINT
            or not alias.exists() or not alias.samefile(target)):
        raise ValueError(f"The short path is occupied or points elsewhere: {alias}. Check it before retrying.")
    return alias


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, help="State directory for project lookup and local upload copies")
    parser.add_argument("workspace", type=Path, help="Builder workspace path, or saved lab ID for unity-project")
    parser.add_argument("action", help="unity-project or a labflow command")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        workspace = locate_pack(args.workspace, args.state_dir) if args.action == "unity-project" else args.workspace
        pack = native_path(workspace.resolve(strict=True))
        if args.action == "unity-project":
            print(unity_project(pack))
        elif args.action in {"approve-gate", "prepare-upload"}:
            approval = argparse.ArgumentParser(prog=f"builder.py WORKSPACE {args.action}")
            approval.add_argument("--lab-id", required=True)
            approval.add_argument("--submitter", help="Name for the two upload folders (defaults to lab ID)")
            approval.add_argument("--knowledge-file", action="append", help="Additional run file relative to knowledge/newknowledge/")
            if args.action == "approve-gate":
                approval.add_argument("--gate", type=int, required=True)
                approval.add_argument("--note", required=True)
                approval.add_argument("--turn-id", required=True)
                approval.add_argument("--notes", type=Path, help="Gate 8 retrospective drafted by the host agent (UTF-8 Markdown)")
            choice = approval.parse_args(args.arguments)
            upload_request = {"submitter": choice.submitter, "knowledge_files": choice.knowledge_file}
            if args.action == "approve-gate":
                if choice.gate != 8 and (choice.notes or choice.submitter or choice.knowledge_file):
                    approval.error("Retrospective and upload options apply to Gate 8 only.")
                if choice.gate == 6:
                    from code_archive import archive
                    print(dump(archive(pack, choice.lab_id, "publish", approval_note=choice.note, turn_id=choice.turn_id)))
                else:
                    message = approve_user_gate(pack, choice.lab_id, choice.gate, choice.note, choice.turn_id,
                                                choice.notes, upload_request if choice.gate == 8 else None)
                    if choice.gate != 8:
                        print(message)
            if args.action == "prepare-upload" or choice.gate == 8:
                try:
                    uploads = prepare_upload(pack, choice.lab_id, args.state_dir or DEFAULT_STATE, upload_request)
                except (OSError, ValueError) as error:
                    raise ValueError(f"Gate 8 upload copies not ready: {error}. Retry prepare-upload for this run.") from error
                uploads["status_line"] = read_builder_status(pack, choice.lab_id)["status_line"]
                print(dump(uploads))
            else:
                print(read_builder_status(pack, choice.lab_id)["status_line"])
        elif args.action == "status" and not any(a in {"-h", "--help"} for a in args.arguments):
            status = json.loads(labflow(pack, "status", *args.arguments))
            status = unified_builder_status(pack, status)
            status["status_line"] = builder_progress(status)
            print(dump(status))
        else:
            code = subprocess.call(builder_command(pack, args.action, *args.arguments), cwd=pack)
            if code == 0 and not any(a in {"-h", "--help"} for a in args.arguments):
                context = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
                context.add_argument("--lab-id")
                target, _ = context.parse_known_args(args.arguments)
                if target.lab_id:
                    print(read_builder_status(pack, target.lab_id)["status_line"], file=sys.stderr)
            sys.exit(code)
    except (ValueError, OSError) as error:
        sys.exit(str(error))
