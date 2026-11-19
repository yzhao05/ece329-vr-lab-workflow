"""Render localized display copies while keeping the machine handoff canonical."""
import json
import re

from ece329_workflow.builder_input import _builder_sections, render_builder_review_pdf
from ece329_workflow.localization import DisplayTranslator, english_pdf, split_display_text, validate_translation_references
from ece329_workflow.model_selection import primary_generator
from ece329_workflow.reporting import build_emvr_task_report, render_emvr_report_pdf


def render_bundle(engine, session, contract, language, translations):
    key = session.design_id
    original = session.design_context.get("idea", {}).get("original", "")
    chinese = re.compile(r"[\u3400-\u9fff]")
    if language == "zh" and session.model_context.get("response_language", "zh") == "zh" and (
            chinese.search(original) or not original):
        return {"design": engine.render_report_pdf(key), "builder": engine.render_builder_input_pdf(key)}
    online = primary_generator(engine.generator) is not None
    if online and translations is None and language == "en":
        translator = DisplayTranslator(engine.generator)
        return {"design": english_pdf(engine, translator, key),
                "builder": english_pdf(engine, translator, key, builder=True)}
    report = build_emvr_task_report(session)
    builder = [contract["document"], _builder_sections(contract), contract["handoff_notes"]]
    strings = {}
    def localize(value):
        if isinstance(value, str):
            translate = chinese.search(value) if language == "en" else (
                not chinese.search(value) and re.search(r"[a-zA-Z]{2,} +[a-zA-Z]{2,}", value))
            if translate:
                return strings.setdefault(value, "")
        if isinstance(value, dict):
            return {k: localize(v) for k, v in value.items()}
        if isinstance(value, (tuple, list)):
            return [localize(v) for v in value]
        return value
    localize([report, builder])
    if translations is not None:
        supplied = json.loads(translations.read_text(encoding="utf-8-sig"))
        if not isinstance(supplied, dict) or set(supplied) != set(strings):
            raise ValueError("Translation keys must match this design revision and target language.")
        strings.update(supplied)
    elif strings:
        if not online:
            return {"translation_required": True, "language": language, "translations": strings}
        translator = DisplayTranslator(engine.generator)
        for source in strings:
            strings[source] = " ".join(translator.translate([part], language)[0] for part in split_display_text(source))
    for source, text in strings.items():
        if not isinstance(text, str) or not text.strip() or bool(chinese.search(text)) != (language == "zh"):
            raise ValueError("Missing translation or incorrect target language: " + source[:65])
        validate_translation_references(source, text)
    rendered = localize(report)
    metadata, sections, notes = localize(builder)
    design_pdf = render_emvr_report_pdf(session, language=language, presentation=rendered)
    builder_pdf = render_builder_review_pdf(metadata, sections, notes, language=language)
    engine.review_artifact(session, rendered, kind="report", language=language, source=report)
    engine.review_artifact(session, [metadata, sections, notes], kind="builder", language=language, source=builder)
    return {"design": design_pdf, "builder": builder_pdf}
