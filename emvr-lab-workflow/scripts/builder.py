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
from xr_import import install_guard, repair_xr_import


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


def check_unity_paths(source, editor_root):
    for asset in source.rglob("*"):
        editor_path = editor_root / asset.relative_to(source)
        if len(str(editor_path).encode("utf-16-le")) // 2 >= 260:
            raise ValueError(f"Unity asset path reaches MAX_PATH through this entry: {editor_path}")


def unity_project(pack, entry_dir=None):
    project = pack / "UnityProject"
    if not native_path(project / "ProjectSettings/ProjectVersion.txt").is_file():
        raise ValueError("Expected a Builder workspace containing UnityProject/ProjectSettings/ProjectVersion.txt")
    if os.name != "nt":
        return project
    import _winapi
    target = native_path(project.resolve(strict=True))
    if target.drive.upper().startswith("\\\\?\\UNC\\"):
        raise ValueError("A persistent Unity junction requires a local project. Move the workspace to a local disk first.")
    key = hashlib.sha256(os.path.normcase(str(target)).encode("utf-8")).hexdigest()[:16]
    local = os.environ.get("LOCALAPPDATA")
    if not entry_dir and not local:
        raise ValueError("LOCALAPPDATA is unavailable. Run unity-project in the Windows account used for Unity Hub.")
    parent = Path(entry_dir).absolute() if entry_dir else Path(local) / "EMVR"
    if native_path(parent).resolve().is_relative_to(target):
        raise ValueError("Choose a short entry directory outside UnityProject.")
    alias = parent / key
    check_unity_paths(target / "Assets", alias / "Assets")
    # Gate 4 runs before Gate 5 copies these trees. Measure the future Unity
    # paths through the Hub entry, including non-BMP Windows filenames.
    specs = native_path(pack) / "LabSpecs"
    for lab in specs.glob("*/workflow_state.json"):
        generated = alias / "Assets/Generated" / lab.parent.name
        for source, destination in (("ApprovedAssets", "ApprovedDependencies"),
                                    ("ReusableFoundation/Gate5MinimalSlice/Source", "Gate5Foundation")):
            check_unity_paths(native_path(pack) / source, generated / destination)
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
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, help="State directory for project lookup and local upload copies")
    parser.add_argument("--entry-dir", type=Path, default=os.environ.get("EMVR_UNITY_ENTRY_DIR"),
                        help="Writable short local directory for Windows Unity project entries")
    parser.add_argument("workspace", type=Path, help="Builder workspace path, or saved lab ID for unity-project")
    parser.add_argument("action", help="unity-project, prepare-editor, repair-xr-import, approve-gate, prepare-upload or a labflow command")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == "unity-project" and args.arguments:
        parser.error("unity-project takes no trailing arguments. Place --entry-dir and --state-dir before WORKSPACE.")
    try:
        workspace = locate_pack(args.workspace, args.state_dir) if args.action == "unity-project" else args.workspace
        pack = native_path(workspace.resolve(strict=True))
        if args.action in {"prepare-editor", "repair-xr-import"}:
            setup = argparse.ArgumentParser(prog=f"builder.py WORKSPACE {args.action}")
            setup.add_argument("--lab-id", required=True)
            choice = setup.parse_args(args.arguments)
            if args.action == "repair-xr-import":
                print(dump(repair_xr_import(pack, choice.lab_id)))
            else:
                status = json.loads(labflow(pack, "status", "--lab-id", choice.lab_id))
                if status.get("current_gate") not in (4, 5) or status.get("evidence", {}).get("gate5_foundation") == "passed":
                    raise ValueError("Prepare editor tools at Gate 4 or before Gate 5A passes.")
                install_guard(pack)
                install_layout_bridge(pack / "UnityProject")
                print("Editor tools ready.")
            sys.exit(0)
        if args.action == "unity-project" or (args.action == "scaffold" and not any(a in {"-h", "--help"} for a in args.arguments)):
            try:
                editor_path = unity_project(pack, args.entry_dir)
            except (OSError, ValueError) as error:
                raise ValueError(f"Unity Editor entry unavailable: {error}. Stop before opening Unity. "
                                 "Retry builder.py with --entry-dir SHORT_WRITABLE_DIRECTORY before WORKSPACE, "
                                 "or run the unity-project command in the user's local terminal.") from error
            if args.action == "unity-project":
                print(editor_path)
                sys.exit(0)
        if args.action in {"approve-gate", "prepare-upload"}:
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
                    published = archive(pack, choice.lab_id, "publish", approval_note=choice.note, turn_id=choice.turn_id)
                    published["status_line"] = read_builder_status(pack, choice.lab_id)["status_line"]
                    print(dump(published))
                else:
                    message = approve_user_gate(pack, choice.lab_id, choice.gate, choice.note, choice.turn_id,
                                                choice.notes, upload_request if choice.gate == 8 else None)
                    if choice.gate != 8:
                        print(message)
                        print(read_builder_status(pack, choice.lab_id)["status_line"])
            if args.action == "prepare-upload" or choice.gate == 8:
                try:
                    uploads = prepare_upload(pack, choice.lab_id, args.state_dir or DEFAULT_STATE, upload_request)
                except (OSError, ValueError) as error:
                    raise ValueError(f"Gate 8 upload copies not ready: {error}. Retry prepare-upload for this run.") from error
                uploads["status_line"] = read_builder_status(pack, choice.lab_id)["status_line"]
                print(dump(uploads))
        elif args.action == "status" and not any(a in {"-h", "--help"} for a in args.arguments):
            status = json.loads(labflow(pack, "status", *args.arguments))
            status = unified_builder_status(pack, status)
            status["status_line"] = builder_progress(status)
            print(dump(status))
        else:
            code = subprocess.call(builder_command(pack, args.action, *args.arguments), cwd=pack)
            if code == 0 and not any(a in {"-h", "--help"} for a in args.arguments):
                if args.action == "scaffold":
                    install_guard(pack)
                    install_layout_bridge(pack / "UnityProject")
                    print(f"unity_editor_project: {editor_path}", flush=True)
                context = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
                context.add_argument("--lab-id")
                target, _ = context.parse_known_args(args.arguments)
                if target.lab_id:
                    print(read_builder_status(pack, target.lab_id)["status_line"], file=sys.stderr)
            sys.exit(code)
    except (ValueError, OSError) as error:
        sys.exit(str(error))
