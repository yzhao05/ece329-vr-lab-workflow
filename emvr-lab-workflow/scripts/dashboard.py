"""Build the four read-only panels from persisted design and Builder state."""
from ece329_workflow.emvr_catalog import course_projection, selection
from ece329_workflow.knowledge_base import KNOWLEDGE
from ece329_workflow.stages import public_stage_catalog
from ece329_workflow.models import InteractionState
from workspace import SNAPSHOT_VERSION


def builder_fingerprint(design):
    if design.get("builder_input_ready"):
        return design["task_report"]["source_design"]["fingerprint"]
    return None


def snapshot(design, builder=None):
    catalog = public_stage_catalog(InteractionState(design["interaction_state"]))
    current = next(s for s in catalog if s["id"] == design["current_stage"])
    groups = {}
    for stage in catalog:
        groups[stage["workflow_stage_number"]] = stage["workflow_stage_title"]
    number = current["workflow_stage_number"]
    done = design["status"] == "complete"
    context = design["design_context"]
    emvr = context.get("emvr_design", {})
    refs = course_projection(emvr).get("course_references", [])
    if not refs and "course_reference_ids" not in emvr.get("explicitly_cleared_fields", []):
        ids = []
        for data in design["stage_outputs"].values():
            payload = data.get("stage_payload", {})
            for ref in payload.get("course_references") or []:
                if isinstance(ref, dict) and ref.get("concept_id"):
                    ids.append(ref["concept_id"])
        refs = KNOWLEDGE.concept_references_for_ids(ids)
    evidence = [{"title": ref["title"], "pages": ref["pages"]} for ref in refs]
    report = design.get("task_report", {})
    notes = []
    idea = report.get("idea") or context.get("idea", {}).get("original")
    if idea:
        notes.append({"label": "实验想法", "value": idea})
    archived = bool(design.get("guided_export_ready"))
    if archived:
        summary = context.get("synthesis", {}).get("student_summary")
        if summary:
            notes.append({"label": "历史设计总结", "value": summary})
    formulas = {f["id"]: f for f in KNOWLEDGE.formulas}
    for role, label in (("primary", "已选主公式"), ("supporting", "已选辅助公式")):
        for formula_id in selection(emvr, role):
            formula = formulas.get(formula_id)
            if formula:
                notes.append({"label": label, "value": f"{formula['name']} · {formula['expression']}"})
    for section in report.get("sections", []):
        if section["stage_id"] in {"BUILDER_IMPLEMENTATION_CONTRACT", "FINAL_QUALITY_REVIEW"}:
            continue
        for item in section["items"]:
            if isinstance(item.get("value"), str) and item.get("value"):
                notes.append({"label": item["label"], "value": item["value"]})
    review = design["quality_review"]
    view = {
        "design_id": design["design_id"], "revision": design["revision"],
        "flow": [{"title": title, "status": "已确认" if done or i < number else
                  "进行中" if i == number else "待开始"} for i, title in groups.items()],
        "builder": builder, "evidence": evidence, "notes": notes,
        "check": {"snapshot_version": SNAPSHOT_VERSION, "status": review.get("status"), "final": bool(review.get("final_review")),
                  "issues": [{"finding": i["finding"], "suggestion": i.get("suggestion", "")}
                             for i in review.get("issues", [])],
                  "report_ready": design.get("report_ready", False), "builder_ready": design.get("builder_input_ready", False)}
    }
    development = context.get("idea_development", {})
    for group, group_number in zip(view["flow"], groups):
        members = [s for s in catalog if s["workflow_stage_number"] == group_number]
        if len(members) < 2:
            continue
        steps = []
        for stage in members:
            facet = stage.get("idea_component_id")
            status = "已确认" if done or stage["number"] < current["number"] else (
                "进行中" if stage["id"] == current["id"] else "待开始")
            if number == group_number and not done and facet in development.get("facets", {}):
                status = "已明确" if development["facets"][facet].get("status") == "CLEAR" else (
                    "进行中" if facet == development.get("active_facet_id") else "待补充")
            steps.append({"title": stage["title"], "status": status, "id": stage["id"]})
        group["steps"] = steps
    view["check"]["details"] = {k: review[k] for k in
        ("causal_chain", "feasibility", "boundary_cases", "option_comparison", "traceability") if k in review}
    versions = design.get("recent_versions", {}).get("versions", [])
    view["check"]["details"]["versions"] = [{"id": v["version_id"], "reason": v.get("reason"),
        "fields": v.get("changed_field_labels", [])} for v in reversed(versions)]
    if archived:
        view["check"]["archived"] = True
    fingerprint = builder_fingerprint(design)
    if fingerprint:
        view["builder_source_fingerprint"] = fingerprint
    return view
