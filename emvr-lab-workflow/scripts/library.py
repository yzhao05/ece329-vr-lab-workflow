"""Search the same package-relative sources listed in the agent instructions."""
import json
import shutil

from ece329_workflow.knowledge_base import KNOWLEDGE


def search(root, query, scope):
    catalog = json.loads((root / "knowledge/catalog.json").read_text(encoding="utf-8"))
    result = {}
    if scope in {"all", "design"}:
        hits = KNOWLEDGE.search(query)
        result["course"] = {key: hits[key] for key in ("concepts", "supplemental_concepts", "formulas")}
    areas = ["updates", "shared_additions"]
    if scope in {"all", "design"}:
        areas.append("design_additions")
    if scope in {"all", "builder"}:
        areas.extend(["builder_guides", "builder_lessons", "builder_archive", "builder_additions"])
    terms = set(query.casefold().split())
    matches = []
    for area in areas:
        for path in sorted((root / catalog[area]).rglob("*")):
            if not path.is_file() or not path.resolve().is_relative_to((root / catalog[area]).resolve()):
                continue
            if path.suffix.lower() not in {".md", ".txt", ".json", ".pdf"}:
                continue
            lines = [] if path.suffix.lower() == ".pdf" else path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            rel = path.relative_to(root).as_posix()
            best_score = 0
            for number, line in enumerate([path.stem, *lines]):
                normalized = line.casefold()
                score = sum(term in normalized for term in terms)
                if score > best_score:
                    best_score = score
                    hit = {"path": rel, "line": number or None, "excerpt": line.strip()[:230]}
                    if score == len(terms):
                        break
            if best_score:
                matches.append((best_score, hit))
    result["documents"] = [hit for _, hit in sorted(matches, key=lambda it: -it[0])[:30]]
    return result



def copy_builder_references(root, pack):
    """Freeze supplementary documentation in this integrated run's own boundary."""
    catalog = json.loads((root / "knowledge/catalog.json").read_text(encoding="utf-8"))
    for area, key in (("shared", "shared_additions"), ("builder", "builder_additions"), ("newknowledge", "updates")):
        source = root / catalog[key]
        for path in sorted(source.rglob("*")):
            if path.suffix.lower() not in {".md", ".txt", ".pdf", ".json"} or not path.is_file():
                continue
            if not path.resolve().is_relative_to(source.resolve()):
                continue
            target = pack / "KnowledgeBase/extensions" / area / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
