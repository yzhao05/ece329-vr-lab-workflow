from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ece329_workflow.engine import WorkflowEngine
from ece329_workflow.openai_generator import generator_from_environment
from ece329_workflow.store import InMemorySessionStore


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "stage_one_dialogues.json"


def evaluate_case(engine, case):
    result = engine.create_design(case["initial"])
    key = result["design_id"]
    if case.get("followup"):
        cards = result["stage_payload"].get("formula_cards", [])
        if len(cards) <= case["selected_index"]:
            return False, "Expected formula candidate was not presented"
        selected = cards[case["selected_index"]]
        turn = {"message": case["followup"]}
        if case.get("send_option_id"):
            turn["selected_option_id"] = selected["option_id"]
        result = engine.process_turn(key, turn)
        flow = engine.store.get(key).design_context["emvr_design"]["formula_flow"]
        passed = selected["profile_id"] in flow["formula_selection"]["primary_profile_ids"]
    elif "formula_phases" in case:
        passed = result["stage_payload"].get("emvr_formula_phase") in case["formula_phases"]
    else:
        passed = result["stage_payload"].get("input_category") == case["expected_category"]
    payload = result["stage_payload"]
    passed = (passed and result["interaction_state"] == case.get("expected_mode", "EMVR_DIRECT")
              and payload.get("request_rejected", False) == case.get("request_rejected", False)
              and case.get("message_contains", "") in result["assistant_message"])
    return passed, f"phase={payload.get('emvr_formula_phase')}, category={payload.get('input_category')}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run paid Stage 1 boundary evaluations against the configured OpenAI model."
    )
    parser.add_argument(
        "--confirm-cost",
        action="store_true",
        help="Confirm that this command may create billable OpenAI API requests.",
    )
    args = parser.parse_args()
    if not args.confirm_cost:
        parser.error("--confirm-cost is required")
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        parser.error("OPENAI_API_KEY is required")

    model_env = dict(os.environ)
    model_env["ECE329_GENERATOR"] = "openai"
    model_env["ECE329_OPENAI_FALLBACK"] = "false"
    generator = generator_from_environment(model_env)
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for case in cases:
        engine = WorkflowEngine(
            generator=generator,
            store=InMemorySessionStore(session_ttl_days=1),
        )
        passed, detail = evaluate_case(engine, case)
        print(f"{'PASS' if passed else 'FAIL'} {case['id']}: {detail}")
        if not passed:
            failures.append(case["id"])

    print(f"\n{len(cases) - len(failures)}/{len(cases)} live evaluations passed.")
    if failures:
        print("Failed cases: " + ", ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
