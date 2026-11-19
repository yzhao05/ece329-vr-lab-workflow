"""Use the run's Builder CLI, or obtain a short Unity Editor project path."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from workspace import approve_user_gate, builder_command, builder_progress, dump, labflow, native_path, read_builder_status


def unity_project(pack):
    project = pack / "UnityProject"
    if not native_path(project / "ProjectSettings/ProjectVersion.txt").is_file():
        raise ValueError("Expected a Builder workspace containing UnityProject/ProjectSettings/ProjectVersion.txt")
    if os.name != "nt":
        return project
    # Map the parent, so Unity opens a named project directory on the drive.
    # Reuse an existing mapping and never replace a drive used by another project.
    for letter in "ZYXWVUTSRQPONMLKJIHGFED":
        drive = Path(letter + ":/")
        if drive.exists() and drive.samefile(pack):
            return drive / project.name
    target = os.path.realpath(pack)
    if target.startswith("\\\\?\\UNC\\"):
        target = "\\\\" + target[8:]
    elif target.startswith("\\\\?\\"):
        target = target[4:]
    for letter in "ZYXWVUTSRQPONMLKJIHGFED":
        drive = Path(letter + ":/")
        if drive.exists():
            continue
        proc = subprocess.run(["subst", drive.drive, target], capture_output=True)
        if proc.returncode == 0 and drive.samefile(pack):
            return drive / project.name
    raise ValueError("Unable to allocate a short Unity drive path. Check free drive letters and access to the workspace.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("action", help="unity-project or a labflow command")
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        pack = native_path(args.workspace.resolve(strict=True))
        if args.action == "unity-project":
            print(unity_project(pack))
        elif args.action == "approve-gate":
            approval = argparse.ArgumentParser(description="Approve the current gate from one user message.")
            approval.add_argument("--lab-id", required=True)
            approval.add_argument("--gate", type=int, required=True)
            approval.add_argument("--note", required=True)
            approval.add_argument("--turn-id", required=True)
            choice = approval.parse_args(args.arguments)
            print(approve_user_gate(pack, choice.lab_id, choice.gate, choice.note, choice.turn_id))
            print(read_builder_status(pack, choice.lab_id)["status_line"])
        elif args.action == "status" and not any(a in {"-h", "--help"} for a in args.arguments):
            status = json.loads(labflow(pack, "status", *args.arguments))
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

