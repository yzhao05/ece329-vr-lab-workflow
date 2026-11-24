"""Prepare the two local upload folders for an accepted Builder run."""
import json
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import tempfile

from code_archive import SOURCE_TYPES
from workspace import ROOT, labflow, lock, native_path, recap_path, remember_upload, unified_builder_status, upload_marker, valid_id


ASSET_SOURCE = SOURCE_TYPES | {
    ".cg", ".glsl", ".glslinc", ".h", ".hpp", ".c", ".cpp", ".m", ".mm",
    ".csinc", ".rsp", ".uxml", ".uss", ".inputactions", ".vfx", ".vfxoperator",
    ".vfxblock", ".dll", ".so", ".dylib", ".a", ".aar", ".jar", ".jslib",
    ".shaderinc", ".raytrace", ".template", ".metal", ".tess", ".java", ".kt", ".swift",
    ".cc", ".cxx", ".inl", ".js", ".ts", ".lua", ".py",
}


def copy_file(source, target, boundary):
    if not source.resolve(strict=True).is_relative_to(boundary.resolve(strict=True)):
        raise ValueError(f"Upload source is outside its directory: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def copy_tree(source, target, boundary, *, unity_assets=False):
    for path in source.iterdir():
        dest = target / path.name
        linked = getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        if linked or path.is_symlink() or not path.resolve(strict=True).is_relative_to(boundary):
            raise ValueError(f"Resolve this linked source before packaging: {path}")
        if path.is_dir():
            if path.name == ".git":
                continue
            copy_tree(path, dest, boundary, unity_assets=unity_assets)
        elif not unity_assets or path.suffix.lower() in ASSET_SOURCE:
            copy_file(path, dest, boundary)
        if unity_assets and dest.exists():
            meta = path.with_name(path.name + ".meta")
            if meta.is_file():
                copy_file(meta, dest.with_name(dest.name + ".meta"), boundary)


def prepare_upload(pack, lab, state, request):
    lab = valid_id(lab)
    if not (pack / "LabSpecs" / lab / "workflow_state.json").is_file():
        raise ValueError("Builder run not found.")
    marker = upload_marker(pack, lab)
    with lock(marker.parent / "approve.lock"):
        status = unified_builder_status(pack, json.loads(labflow(pack, "status", "--lab-id", lab)))
        if not (status.get("workflow_complete") or status.get("upload_pending")):
            raise ValueError("Gate 8 acceptance and retrospective archiving must finish first.")
        digest = status["evidence"]["compile_content_digest"]
        saved = remember_upload(pack, lab, digest, request)
        delivery = copy_upload(pack, lab, state, status, saved.get("submitter"), saved.get("knowledge_files", []))
        marker.unlink()
        return delivery


def copy_upload(pack, lab, state, status, submitter, knowledge_files):
    name = (submitter or lab).strip()
    if not re.fullmatch(r"[\w -]{1,80}", name):
        raise ValueError("Use letters, numbers, spaces, hyphens or underscores for the submission name.")
    digest = status["evidence"]["compile_content_digest"]
    if not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError("Missing accepted build fingerprint.")
    version = Path(lab) / digest
    code_root = native_path(ROOT / "reusable-code/newcode").resolve()
    knowledge_root = native_path(ROOT / "knowledge/newknowledge").resolve()
    recap = recap_path(pack, lab, status).relative_to("knowledge/newknowledge")
    project = native_path(pack / "UnityProject").resolve(strict=True)
    manifest = project / "Packages/manifest.json"
    dependencies = json.loads(manifest.read_text(encoding="utf-8-sig"))["dependencies"]
    package_dirs = {project / "Packages"}
    if (project / "LocalPackages").is_dir():
        package_dirs.add(project / "LocalPackages")
    for spec in dependencies.values():
        if spec.startswith("file:"):
            local = (manifest.parent / spec[5:]).resolve(strict=True)
            if not local.is_relative_to(project) or local == project:
                raise ValueError(f"Local package needs an in-project source for handoff: {spec}")
            if not any(local.is_relative_to(folder) for folder in package_dirs):
                package_dirs.add(local)

    dest = native_path(state.resolve()) / "uploads" / lab
    if any(dest.resolve().is_relative_to(root) for root in (project, code_root, knowledge_root)):
        raise ValueError("Select a state directory outside the upload sources.")
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest) as tmp:
        staging = Path(tmp) / "ready"
        code = staging / (name + "_newcode") / version
        knowledge = staging / (name + "_newknowledge")
        copy_tree(code_root / version, code, code_root)
        if not code.exists():
            raise ValueError("The Gate 6 archive is empty.")
        unity = code / "UnityProject"
        copy_tree(project / "Assets", unity / "Assets", project, unity_assets=True)
        for folder in sorted(package_dirs):
            target = unity / folder.relative_to(project)
            if folder.is_dir():
                copy_tree(folder, target, project)
            else:
                copy_file(folder, target, project)
        copy_file(project / "ProjectSettings/ProjectVersion.txt", unity / "ProjectSettings/ProjectVersion.txt", project)
        for relative in [recap, *map(Path, knowledge_files)]:
            if relative.is_absolute() or PureWindowsPath(relative).anchor or ".." in relative.parts:
                raise ValueError("Knowledge files must be relative to knowledge/newknowledge/.")
            copy_file(knowledge_root / relative, knowledge / relative, knowledge_root)
        current = json.loads(labflow(pack, "status", "--lab-id", lab))
        if not current.get("workflow_complete") or current["evidence"]["compile_content_digest"] != digest:
            raise ValueError("The accepted build changed while preparing the upload.")
        # A new delivery never overwrites a user's previous upload copies.
        delivery = dest / ("handoff-" + Path(tmp).name)
        staging.rename(delivery)
    return {"lab_id": lab, "knowledge_update": status["knowledge_update"],
            "newcode": str(delivery / (name + "_newcode")),
            "newknowledge": str(delivery / (name + "_newknowledge"))}
