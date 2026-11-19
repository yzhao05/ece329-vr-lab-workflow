# ECE329 runtime knowledge catalog

This directory contains compact, deployable reference catalogs. The delivery package includes the source PDFs in `knowledge/sources/` and workflow updates in `knowledge/newknowledge/`, relative to the package root.

## Source hierarchy

1. `source_manifest.json` identifies `ece329lecture_notes.pdf`. The lecture notes define the ECE329 course boundary and the formulas that have been explicitly verified for formula-bearing stages.
2. `supplemental_sources.json` identifies verified supplemental references and stores paraphrased concept summaries, relationship examples, source sections, PDF page ranges, hashes, and mappings back to course-scope concept IDs.
3. Entries under `candidate_sources_not_used_for_retrieval` are bibliographic leads only. They are not included in model retrieval until a legal full text is supplied and its contents and pages are checked.

## Runtime files

- `concepts.json`: 39 lecture units, keywords, concepts, lecture-grounded brainstorming axes, and an extensible catalog of basic comparison-case bundles. Each bundle carries course concept IDs; conversation code handles adoption and modification generically rather than branching on its topic.
- `formulas.json`: canonical formulas with IDs, conditions, course concept mappings, and PDF pages.
- `formula_design_profiles.json`: formula-centered experiment-design profiles. Each
  profile distinguishes primary and supporting formulas and records supported
  variations, observations, and boundary conditions; all formula IDs resolve back to
  `formulas.json`.
- `scene_formula_links.json`: legacy exploration scene bindings to formula profiles.
  The runtime merges these with the authored Guided extension before resolving
  selections and filtering the sampling pool by course domain.
- `experiment_design_patterns.json`: 15 finite experiment-design paradigms and an
  explicit applicability map for every formula profile. EMVR uses this layer to
  generate a coverage matrix and runtime experiment methods after formula
  confirmation; it does not sample the fixed scene catalog.
- `scene_templates.json`: extensible Stage 1 physical-scene templates selected by catalog keywords, plus topic-independent fallback frames. New course topics are added as data instead of Python conditionals.
- `guided_formula_pattern_scenes.json`: 45 authored Guided scenes covering all 32
  formula profiles and all 15 applicable experiment paradigms. Each declares its
  primary formulas, profile, pattern, distinctive question and complete physical
  picture. Supporting profiles add explicit cross-formula evidence where needed.
  These scenes use their own bound picture rather than a generic keyword fallback.
- `source_manifest.json`: identity and extraction policy for the course-scope lecture notes.
- `supplemental_sources.json`: enabled supplemental sources and multi-source Stage 1 relationship catalog.

## Historical Guided records

The 183 stable scene IDs include 117 lecture axes, 21 supplemental relationships and 45 formula-pattern scenes. Older records refer to the original 138 entries as `ECE329-S001`–`ECE329-S138` and the extension as `ECE329-S139`–`ECE329-S183`. Preserve these IDs when maintaining the catalogs. The A/B/C alternatives in archived Guided sessions came from this pool.

New designs use the EMVR formula-first flow and the applicable experiment-design patterns described above.

## Supplemental-source policy

- A supplemental concept must map to at least one valid `course_scope_concept_id`.
- A relationship example must cite an enabled source, section, and valid PDF page range.
- Stage 1 can use these relationships as examples and invite the student to suggest another relationship.
- Supplemental summaries do not authorize formula invention. Add a formula only through the separately reviewed formula-catalog process.
- Do not copy textbook prose into this catalog. Store short paraphrases, labels, and locators only.

## Local source files used for the current extraction

The following reference PDFs are available locally under `knowledge/sources/` relative to the delivery-package root:

- `BOOK_ElectromagneticWaveTheory_by_JINAUKONG_FreeRelease2021.pdf`
- `EMandApp_DavidH.pdf`
- `getfile.pdf` (original download name: `getfile.asp`)

Run the test suite after any catalog change. `LectureKnowledgeBase.validate()` checks IDs, course-scope mappings, source IDs, PDF page bounds, comparison bundles, and scene-template completeness.
