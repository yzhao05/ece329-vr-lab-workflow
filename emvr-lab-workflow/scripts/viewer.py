"""Open or resume the local, read-only Design and Builder viewer."""
import argparse
import hashlib
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit
from urllib.request import ProxyHandler, build_opener
import webbrowser

from workspace import DEFAULT_STATE, ROOT, SNAPSHOT_VERSION, active_builder, dump, lock, native_path, read_builder_status, run_directory, valid_id, write_json
from scene_layout import scene_layout


VIEWER_PROTOCOL = 11
PREVIEW_ASSETS = {"scene-preview.js", "vendor/three-0.160.1/three.module.min.js", "vendor/three-0.160.1/OrbitControls.js"}
WEB_ASSETS = {"index.html", "style.css", "stages.json", "viewer.js"} | PREVIEW_ASSETS


def web_asset(web, name):
    asset = web / name
    # Custom web roots from the four-panel viewer predate the optional 3D modules.
    if name in PREVIEW_ASSETS and not asset.is_file():
        return ROOT / "web" / name
    return asset


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def session_file(state, token):
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid viewer session")
    return state / "viewer/sessions" / (token + ".json")


def saved_revision(state, key):
    database = state / "design.sqlite3"
    if not database.is_file():
        return None
    # A turn commits before it publishes the snapshot. Read only the indexed
    # revision on each poll so an interrupted publication can recover.
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        row = connection.execute("SELECT revision FROM design_sessions WHERE design_id = ?", (key,)).fetchone()
    return row[0] if row else None


def snapshot_is_current(revision, view):
    check = view.get("check", {})
    needs_fingerprint = check.get("builder_ready") or view.get("builder")
    return (revision == view.get("revision") and "details" in check and check.get("snapshot_version") == SNAPSHOT_VERSION
            and (not needs_fingerprint or bool(view.get("builder_source_fingerprint"))))


def live_design(state, web, key):
    path = web / "data" / (key + ".json")
    view = read_json(path)
    revision = saved_revision(state, key)
    if revision is None:
        return view  # Shared snapshots can outlive their private Builder workspace.
    if not snapshot_is_current(revision, view):
        # Only upgrade an already published record. A GET cannot expose other saved designs.
        restore_saved_view(state, web, key)
        view = read_json(path)
    previous = view.get("builder")
    fingerprint = view.get("builder_source_fingerprint") or (previous or {}).get("source_fingerprint")
    if not fingerprint:
        return view
    status = active_builder(state, key, fingerprint)
    if status == previous:
        return view
    # Native checks can take time. Compare the snapshot again before publishing
    # so a poll cannot overwrite a Design turn committed during those checks.
    with lock(state / "locks" / (key + ".lock")):
        latest = read_json(path)
        if latest != view:
            return latest
        view["builder_source_fingerprint"] = fingerprint
        view["builder"] = status
        write_json(path, view)
    return view


def restore_saved_view(state, web, key):
    # Called by an explicit open, or to upgrade a snapshot already published.
    path = web / "data" / (key + ".json")
    with lock(state / "locks" / (key + ".lock")):
        revision = saved_revision(state, key)
        if revision is None:
            return
        if path.is_file():
            view = read_json(path)
            if snapshot_is_current(revision, view):
                return
        from workflow import WorkflowEngine, HostAgentGenerator, SQLiteSessionStore, project_view
        from ece329_workflow.models import SessionNotFound
        engine = WorkflowEngine(generator=HostAgentGenerator(), store=SQLiteSessionStore(state / "design.sqlite3", session_ttl_days=None))
        try:
            design = engine.get_design(key)
        except SessionNotFound:
            return
        write_json(path, project_view(state, design))


def instance_file(state, web):
    digest = hashlib.sha256(os.fsencode(str(web))).hexdigest()[:24]
    return state / "viewer" / (digest + ".json")


def handler(state, web, nonce):
    types = {".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json"}

    class ViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            request = urlsplit(self.path)
            path = request.path.removeprefix("/")
            geometry = parse_qs(request.query).get("geometry", [None])[0]
            try:
                if not path or path in WEB_ASSETS:
                    asset = web_asset(web, path or "index.html")
                    body, mime = asset.read_bytes(), types[asset.suffix]
                else:
                    if path == "_instance":
                        value = {"instance": nonce}
                    elif path.startswith("_session/"):
                        entry = read_json(session_file(state, path.removeprefix("_session/")))
                        if "workspace" in entry:
                            pack = Path(entry["workspace"])
                            lab = entry["lab_id"]
                            initialized = native_path(pack / "LabSpecs" / lab / "workflow_state.json").is_file()
                            value = {"standalone": True, "builder": read_builder_status(pack, lab) if initialized else None}
                            if initialized:
                                value["layout"] = scene_layout(pack, lab, geometry)
                        else:
                            value = {"design_id": entry.get("design_id")}
                    elif path == "data/latest.json":
                        value = read_json(web / path)
                    elif re.fullmatch(r"data/[A-Za-z0-9_-]{1,80}\.json", path):
                        key = Path(path).stem
                        value = live_design(state, web, key)
                        builder = value.get("builder") or {}
                        fingerprint = builder.get("source_fingerprint")
                        if fingerprint and builder.get("lab_id"):
                            value["layout"] = scene_layout(run_directory(state, key, fingerprint), builder["lab_id"], geometry)
                    else:
                        self.send_error(404)
                        return
                    if geometry is not None:
                        body = value.get("layout")
                        if not isinstance(body, bytes):
                            self.send_error(404)
                            return
                        mime = "application/octet-stream"
                    else:
                        body, mime = json.dumps(value, ensure_ascii=False).encode("utf-8"), types[".json"]
            except FileNotFoundError:
                self.send_error(404)
                return
            except (OSError, ValueError, KeyError, sqlite3.Error):
                self.send_error(503, "Workflow status temporarily unavailable")
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    return ViewerHandler


def read_registration(marker):
    try:
        info = read_json(marker)
    except (FileNotFoundError, ValueError):
        return {}
    if not isinstance(info, dict) or not isinstance(info.get("instance"), str) or not info["instance"]:
        return {}
    if type(info.get("port")) is not int or not 1 <= info["port"] <= 65535:
        return {}
    return info


def serve(state, web, nonce, port):
    marker = instance_file(state, web)
    with ThreadingHTTPServer(("127.0.0.1", port), handler(state, web, nonce)) as server:
        server.timeout = 0.5
        write_json(marker, {"instance": nonce, "port": server.server_port, "protocol": VIEWER_PROTOCOL})
        while read_registration(marker).get("instance") == nonce:
            server.handle_request()


def running_url(info):
    try:
        port = int(info["port"])
        url = f"http://127.0.0.1:{port}/"
        with build_opener(ProxyHandler({})).open(url + "_instance", timeout=1) as response:
            identity = json.load(response)
            if isinstance(identity, dict) and identity.get("instance") == info["instance"]:
                return url
    except (OSError, ValueError, KeyError):
        pass
    return None


def launch(state, web):
    for asset in sorted(WEB_ASSETS):
        location = web_asset(web, asset)
        if not location.is_file():
            raise ValueError(f"Missing viewer asset: {location}")
    marker = instance_file(state, web)
    with lock(marker.with_suffix(".lock")):
        info = read_registration(marker)
        url = running_url(info)
        if url and info.get("protocol") == VIEWER_PROTOCOL:
            return url
        port = 0
        if url:
            # Replace an older local worker on its own verified port. Open
            # tabs and bound design sessions retain their URLs after upgrade.
            marker.unlink()
            for _ in range(80):
                if not running_url(info):
                    break
                time.sleep(0.1)
            else:
                raise OSError("Previous viewer is still stopping")
            port = int(info["port"])
        nonce = secrets.token_hex(16)
        args = [sys.executable, str(Path(__file__).resolve()), "--state-dir", str(state),
                "--web-dir", str(web), "serve", nonce, "--port", str(port)]
        log = marker.with_suffix(".log")
        with log.open("ab") as output:
            worker = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                start_new_session=os.name != "nt", close_fds=True)
        for _ in range(100):
            if worker.poll() is not None:
                break
            info = read_registration(marker)
            url = running_url(info) if info.get("instance") == nonce else None
            if url:
                return url
            time.sleep(0.1)
        raise OSError(f"Viewer did not start. See {log}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--web-dir", type=Path, default=ROOT / "web")
    commands = parser.add_subparsers(dest="cmd", required=True)
    worker = commands.add_parser("serve", help=argparse.SUPPRESS)
    worker.add_argument("nonce")
    worker.add_argument("--port", type=int, default=0)
    commands.add_parser("close")
    opening = commands.add_parser("open")
    target = opening.add_mutually_exclusive_group()
    target.add_argument("design_id", nargs="?", type=valid_id)
    target.add_argument("--new", action="store_true")
    target.add_argument("--builder-workspace", type=Path)
    opening.add_argument("--lab-id", type=valid_id)
    opening.add_argument("--url-only", action="store_true", help="Open the returned URL in the host browser instead")
    args = parser.parse_args()
    state, web = args.state_dir.resolve(), args.web_dir.resolve()
    if args.cmd == "serve":
        serve(state, web, args.nonce, args.port)
        return
    if args.cmd == "close":
        marker = instance_file(state, web)
        with lock(marker.with_suffix(".lock")):
            marker.unlink(missing_ok=True)
        return
    if bool(args.builder_workspace) != bool(args.lab_id):
        parser.error("--builder-workspace and --lab-id must be used together")
    url = launch(state, web)
    result = {}
    if args.new or args.builder_workspace:
        token = secrets.token_hex(16)
        entry = {"design_id": None} if args.new else {"workspace": str(args.builder_workspace.resolve()), "lab_id": args.lab_id}
        write_json(session_file(state, token), entry)
        url += "?session=" + token
        result["viewer_session"] = token
    elif args.design_id:
        restore_saved_view(state, web, args.design_id)
        url += "?design=" + args.design_id
    result["url"] = url
    opened = False if args.url_only else webbrowser.open(url, new=2)
    result["browser_opened"] = bool(opened)
    print(dump(result), flush=True)
    if not opened and not args.url_only:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(str(error))

