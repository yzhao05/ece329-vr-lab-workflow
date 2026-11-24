"""Portable command-line adapter for an agent hosting the EMVR workflow."""
from contextlib import nullcontext
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys
import tempfile

from workspace import DEFAULT_STATE, BASE, ROOT, SKILL, dump, labflow, lock, native_path, run_directory, valid_id, write_json
sys.path.insert(0, str(SKILL / "design/src"))
from ece329_workflow.builder_input import build_builder_gate1_input
from ece329_workflow.dialogue_state import current_pending_action
from ece329_workflow.engine import WorkflowEngine
from ece329_workflow.models import InteractionState, Stage, WorkflowError
from ece329_workflow.stages import stage_group_metadata, stage_title
from ece329_workflow.store import SQLiteSessionStore
from ece329_workflow.experience import ExperienceStore, FeedbackService, ModelExperienceExtractor
from workspace import active_builder, publish_directory
from dashboard import snapshot, builder_fingerprint
from scene_layout import install_layout_bridge
from library import copy_builder_references, search
from host_agent import HostAgentGenerator

AGENT_FIELDS = ("design_id", "revision", "turn_id", "workflow_stage_title", "stage_status",
                "assistant_message", "student_task", "stage_payload", "warnings", "completion_error",
                "workflow_status", "report_ready", "builder_input_ready")


class AgentWorkflowEngine(WorkflowEngine):
    def _attach_experiences(self, session, message):
        super()._attach_experiences(session, message)
        # Keep the selection from the actual turn across short-lived CLI processes.
        rules = session.turn_context.get("experience_rules", [])
        session.turn_context["host_experience_rules"] = rules
        session.model_context["host_experience_rules"] = rules


def project_view(state, design):
    return snapshot(design, active_builder(state, design["design_id"], builder_fingerprint(design)))


def design_status_line(design, reply):
    stage = Stage(design["current_stage"])
    mode = InteractionState(design["interaction_state"])
    group = stage_group_metadata(stage, mode)
    titles = list(dict.fromkeys([group["workflow_stage_title"], stage_title(stage, mode)]))
    current = design["stage_outputs"].get(stage.value, {})
    pending = (current.get("stage_payload") or {}).get("pending_action") or {}
    if design["status"] == "complete":
        status = "已完成"
    elif reply.get("completion_error"):
        status = "待补充"
    elif pending.get("type") == "CONFIRM_STAGE_OR_MODIFY" or pending.get("default_option_id"):
        status = "待讨论或确认草稿"
    else:
        status = "讨论中"
    return f"Design · Gate {group['workflow_stage_number']}/{group['workflow_stage_count']} · {' / '.join(titles)} · {status}"


def handoff(engine, design, state, start_builder, language=None, translations=None):
    if design.get("guided_export_ready"):
        raise ValueError("这份历史设计已归档。要生成 Builder 输入，请在统一工作流中创建并确认 VR 方案。")
    if not (design["report_ready"] and design["builder_input_ready"]):
        raise ValueError("请先完成并确认完整方案，再导出或交给 Builder。")
    key = design["design_id"]
    session = engine.store.get(key)
    contract = build_builder_gate1_input(session)
    stamp = contract["document"]["source_design"]
    lab = {i["key"]: i["value"] for i in contract["identity"]}
    language = language or session.model_context.get("response_language", "zh")
    base = state / "handoffs" / key
    base.mkdir(parents=True, exist_ok=True)
    folder = base / (str(stamp["revision"]) + "-" + stamp["fingerprint"])
    # A translation is a separate presentation of the same approved design.
    folder = folder.with_name(folder.name + "-" + language)
    contract_name = "builder-gate1-input.json"
    # A saved design may predate a correction to how its inventory is rendered.
    # Deliver corrected files separately; a running Builder keeps its approved inputs.
    old_contract = folder / contract_name
    previous = contract
    if old_contract.is_file():
        try:
            previous = json.loads(old_contract.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError):
            previous = None
    if previous != contract:
        edition = hashlib.sha256(dump(contract).encode("utf-8")).hexdigest()[:12]
        folder = folder.with_name(folder.name + "-" + edition)
    pdfs = {"design.pdf": "design", "builder-gate1-input.pdf": "builder"}
    missing_pdfs = [name for name in pdfs if not (folder / name).is_file()]
    if missing_pdfs:
        from export_language import render_bundle
        rendered = render_bundle(engine, session, contract, language, translations)
        if "translation_required" in rendered:
            return rendered
        with tempfile.TemporaryDirectory(dir=base) as tmp:
            bundle = Path(tmp) / "delivery"
            bundle.mkdir()
            for name in missing_pdfs:
                (bundle / name).write_bytes(rendered[pdfs[name]])
            if not folder.exists():
                write_json(bundle / contract_name, contract)
                publish_directory(bundle, folder)
            else:
                for name in missing_pdfs:
                    (bundle / name).replace(folder / name)
    if not (folder / contract_name).is_file():
        write_json(folder / contract_name, contract)
    result = {"artifacts": str(folder), "revision": stamp["revision"], "language": language}
    if not start_builder:
        return result
    # Return the same long-path-capable root that Builder uses internally.
    # Even when the workspace itself is short enough, files below it may not be.
    pack = native_path(run_directory(state, key, stamp["fingerprint"]))
    if not pack.exists():
        pack.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=pack.parent) as tmp:
            staged = Path(tmp) / BASE.name
            shutil.copytree(native_path(BASE), staged, ignore=shutil.ignore_patterns(
                "__pycache__", ".pytest_cache", "RebuildWorkspaces", "legacy-lab-specific-summaries"))
            copy_builder_references(ROOT, staged)
            labflow(staged, "new", "--lab-id", lab["lab_id"], "--title", lab["title"], "--domain",
                    lab["domain"], "--scene", f"Assets/Scenes/{lab['lab_id']}.unity", "--mode", "integrated-development",
                    "--manual-language", "English" if language == "en" else "简体中文")
            install_layout_bridge(staged / "UnityProject")
            inputs = staged / "LabSpecs" / lab["lab_id"] / "design-input"
            inputs.mkdir()
            for name in (*pdfs, contract_name):
                shutil.copy2(folder / name, inputs / name)
            publish_directory(staged, pack)
    inputs = pack / "LabSpecs" / lab["lab_id"] / "design-input"
    for name in (*pdfs, contract_name):
        if not (inputs / name).is_file():
            raise ValueError(f"Saved Builder input is missing: {inputs / name}")
    result["builder_inputs_match_export"] = all(
        (inputs / name).read_bytes() == (folder / name).read_bytes() for name in (*pdfs, contract_name))
    write_json(state / "runs" / key / "active.json", {"fingerprint": stamp["fingerprint"], "lab_id": lab["lab_id"]})
    result["design_id"] = key
    result["lab_id"] = lab["lab_id"]
    result["builder_workspace"] = str(pack)
    result["builder_inputs"] = str(inputs)
    return result


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("host", "environment"), default="host")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--web-dir", type=Path, default=ROOT / "web", help="Static viewer root to update")
    commands = parser.add_subparsers(dest="cmd", required=True)
    create = commands.add_parser("create")
    create.add_argument("idea")
    create.add_argument("--viewer-session", help="Bind the page opened for this new design")
    create.add_argument("--language", choices=["zh", "en"])
    turn = commands.add_parser("turn")
    turn.add_argument("id", type=valid_id)
    inputs = turn.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--message")
    inputs.add_argument("--stdin-json", action="store_true")
    turn.add_argument("--complete-stage", action="store_true")
    turn.add_argument("--language", choices=["zh", "en"])
    turn.add_argument("--option")
    turn.add_argument("--turn-id")
    for name in ("show", "feedback", "retrospective", "export", "builder-init"):
        entry = commands.add_parser(name)
        entry.add_argument("id", type=valid_id)
        if name in ("export", "builder-init"):
            entry.add_argument("--language", choices=["en", "zh"])
            entry.add_argument("--translations", type=Path)
        if name == "retrospective":
            entry.add_argument("--notes", type=Path, required=True)
        if name == "feedback":
            entry.add_argument("--submit", action="store_true", help="Read a feedback record from JSON stdin")
    processing = commands.add_parser("feedback-process")
    processing.add_argument("--ticket", help="Prepare this report for analysis by the host agent")
    processing.add_argument("--candidate", type=Path, help="Reviewed host analysis of this ticket")
    review = commands.add_parser("experience-review")
    review.add_argument("experience_id", help="Rule selected by the maintainer for review")
    kb = commands.add_parser("knowledge")
    kb.add_argument("query")
    kb.add_argument("--scope", choices=["all", "design", "builder"], default="all")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.cmd == "knowledge":
        if not args.query.strip():
            raise ValueError("请输入检索词。")
        return search(ROOT, args.query, args.scope)
    state = args.state_dir.resolve()
    generator = HostAgentGenerator() if args.provider == "host" else None
    engine = AgentWorkflowEngine(generator=generator, store=SQLiteSessionStore(state / "design.sqlite3", session_ttl_days=None))
    engine.project_id = os.environ.get("ECE329_PROJECT_ID", "default").strip() or "default"
    experience = ExperienceStore(engine.store.path, project_id=engine.project_id)
    engine.experience_store = experience
    if args.cmd == "experience-review":
        body = json.load(sys.stdin)
        return experience.review(args.experience_id, **body)
    if args.cmd == "feedback-process":
        if args.ticket:
            from ece329_workflow.experience import candidate_schema, validate_candidate
            detail = experience.feedback_detail(args.ticket)
            if args.candidate is None:
                return {"ticket": detail, "candidate_schema": candidate_schema()}
            proposal = json.loads(args.candidate.read_text(encoding="utf-8-sig"))
            if proposal.get("ticket_id") != args.ticket:
                raise ValueError("Candidate does not refer to this feedback ticket.")
            candidate = validate_candidate(proposal.get("candidate"))
            job = experience.claim(ticket_id=args.ticket)
            if job is not None:
                experience.finish(job, candidate)
            return experience.feedback_detail(args.ticket)
        if args.candidate:
            raise ValueError("--candidate requires --ticket.")
        feedback = FeedbackService(experience, ModelExperienceExtractor(engine.generator), background=False)
        if not feedback.extractor.available_models():
            raise ValueError("Feedback analysis requires a configured environment provider; queued reports are retained.")
        return {"processed": feedback.run_once()}
    if args.cmd == "feedback":
        session = engine.store.get(args.id)
        if args.submit:
            ticket, _ = experience.submit(session, json.load(sys.stdin))
            return ticket
        return {"tickets": experience.tickets(args.id)}
    if args.cmd == "create":
        from viewer import session_file, read_json
        page = session_file(state, args.viewer_session) if args.viewer_session else None
        with lock(page.with_suffix(".lock")) if page else nullcontext():
            entry = read_json(page) if page else {"design_id": None}
            if "design_id" not in entry:
                raise ValueError("This page belongs to a standalone Builder run.")
            if entry["design_id"]:
                key = entry["design_id"]
                args.cmd, reply = "show", {}
            else:
                language = args.language or ("zh" if re.search(r"[\u3400-\u9fff]", args.idea) else "en")
                reply = engine.create_design(args.idea, language=language)
                key = reply["design_id"]
                if page:
                    write_json(page, {"design_id": key})
    else:
        key = args.id
        reply = {}
    with lock(state / "locks" / (key + ".lock")):
        if args.cmd == "turn":
            if args.stdin_json:
                if args.complete_stage or args.option or args.turn_id or args.language:
                    raise ValueError("Use either structured stdin or command-line turn options.")
                request = json.load(sys.stdin)
                if not isinstance(request, dict):
                    raise ValueError("A turn must be a JSON object.")
                if generator is not None and "interpretation" not in request:
                    raise ValueError("The host agent must supply interpretation with each structured turn.")
            else:
                request = {"message": args.message, "complete_stage": args.complete_stage,
                           "selected_option_id": args.option, "turn_id": args.turn_id}
                if args.language:
                    request["language"] = args.language
            if "interpretation" in request:
                if generator is None:
                    raise ValueError("Structured interpretation requires the host provider.")
                generator.set_interpretation(request.pop("interpretation"))
            reply = engine.process_turn(key, request)
        design = engine.get_design(key)
        result = {k: reply[k] for k in AGENT_FIELDS if k in reply}
        if args.cmd in {"export", "builder-init"}:
            result.update(handoff(engine, design, state, args.cmd == "builder-init", args.language, args.translations))
        view = project_view(state, design)
        result["status_line"] = (view["builder"]["status_line"] if args.cmd in {"show", "builder-init"} and view.get("builder")
                                 else design_status_line(design, reply))
        if args.cmd == "retrospective":
            builder = view.get("builder") or {}
            if builder.get("retrospective_pending"):
                raise ValueError("Finish the pending Gate 8 archive with builder.py approve-gate --gate 8 --notes FILE.")
            if not design.get("report_ready") or not builder.get("knowledge_update"):
                raise ValueError("Complete the confirmed Design and all Builder gates including Gate 8 first.")
            # Older hosts may replay this command after Gate 8. Only the
            # gate approval publishes the retrospective for the accepted run.
            rel = builder["knowledge_update"]
            if args.notes.read_text(encoding="utf-8-sig").strip() != (ROOT / rel).read_text(encoding="utf-8-sig").strip():
                raise ValueError("Gate 8 already archived a different retrospective at " + rel)
            return {"knowledge_update": rel}
        if args.cmd in ("create", "turn", "show"):
            saved = engine.store.get(key)
            pending = current_pending_action(saved) or {}
            result["next_input"] = {field: pending[field] for field in ("type", "answer_fields", "question")
                                    if field in pending} if design["status"] != "complete" else {}
            rules = reply.get("experience_rules", saved.model_context.get("host_experience_rules", []))
            result["experience_rules"] = [r for r in rules if engine.experience_store.rule_is_current(r)]
        write_json(args.web_dir / "data" / (key + ".json"), view)
        write_json(args.web_dir / "data/latest.json", {"design_id": key})
        if args.cmd == "show":
            result.update(view)
            result["workflow_status"] = design["status"]
            if engine.store.get(key).interaction_state is InteractionState.EMVR_DIRECT:
                current = design["stage_outputs"].get(design["current_stage"], {})
                result.update({k: current[k] for k in ("assistant_message", "student_task", "stage_payload", "warnings") if k in current})
        result["viewer"] = f"index.html?design={key}"
        return result


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8-sig")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        print(dump(main()))
    except (ValueError, WorkflowError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

