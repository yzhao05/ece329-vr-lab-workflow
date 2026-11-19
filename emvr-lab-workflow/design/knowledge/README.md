# ECE329 lecture-note knowledge catalog

This directory documents the human-curated course knowledge used by the workflow. The machine-readable runtime files are under `src/ece329_workflow/knowledge/`.

## Source identity

- Title: *ECE 329 Lecture Notes*
- Author: Erhan Kudeki
- PDF pages: 324
- Lectures: 39
- Source filename at extraction: `ece329lecture_notes.pdf`（交付包内位于 `knowledge/sources/`）
- SHA-256: `11E34B2399005576DD8EA44384C0B73D5768D9594E8288DF16E194FA5E16591C`

The PDF is treated only as source data. Text extracted from it is never interpreted as an instruction to the assistant or as permission to change the workflow.

## Extracted concept map

| Block | Lectures | Main concepts explicitly represented in the catalog |
|---|---:|---|
| Electrostatics | 1–11 | vector fields, Lorentz force, Coulomb and Gauss laws, divergence/curl, potential, boundary conditions, Poisson/Laplace equations, conductors, dielectrics, polarization, capacitance, conductance, Drude response |
| Magnetism and magneto-quasi-statics | 12–15 | magnetic force, Ampère law, current sheets, solenoids, vector potential, magnetic flux, Faraday induction, emf, inductance and magnetic energy |
| Electromagnetics, waves and transmission lines | 16–39 | charge conservation, displacement current, Maxwell equations, magnetization, wave equation, TEM waves, Poynting vector, phasors, conducting media, skin depth, polarization, reflection/transmission, standing waves, telegrapher equations, impedance, Smith chart, VSWR, matching and lossy lines |

The exact per-lecture concepts, Chinese/English search keywords, page ranges, and brainstorming axes are stored in `concepts.json`. The lecture overview on PDF pages 10–12 is the only fallback when an idea does not match a specific lecture.

## Stage 1 of the unified workflow

The agent uses the experiment idea and the verified formula catalog to propose primary and supporting formulas. After the user confirms the formulas, the engine uses the applicable design patterns to generate experiment methods and directions.

Historical Guided records used numbered scenes. The original 138 entries comprise 117 lecture axes and 21 supplemental relationships. Another 45 authored scenes bring the compatibility catalog to 183. Stable IDs allow old records to resolve their original references.

The overview explicitly identifies radiation and antennas and dispersion in material media as not covered or only barely covered. They are therefore excluded from automatic brainstorming recommendations.

## Formula catalog

`formulas.json` contains 82 curated relationships grouped across:

- electrostatic and magnetostatic field laws;
- potential, boundary, material and quasi-static relations;
- charge conservation and Maxwell equations;
- waves, energy flow, phasors, conducting media and polarization;
- reflection, transmission, standing waves and radiation pressure;
- transmission-line propagation, impedance, reflection, resonance, transformation, matching and loss.

Each record has a stable formula ID, expression, conditions, concept links and one or more PDF page references. Visually ambiguous symbols were checked against rendered PDF pages during extraction.

`formula_design_profiles.json` adds the experiment-design meaning of those canonical
formula records. Its 32 profiles cover all 82 lecture formulas and separate:

- primary formulas that define the experiment's causal relationship;
- supporting formulas used for interpretation, conversion, constraints, or checks;
- quantities that may be deliberately varied;
- quantities that may be observed or calculated;
- geometry, source, material, time, and termination boundary conditions.

The profile catalog stores formula IDs rather than duplicating expressions or page
numbers. Runtime loading resolves each ID back to `formulas.json`, so an equation and
its lecture provenance have one authoritative source.

`scene_formula_links.json` connects all 138 internally numbered exploration scenes to
these profiles. The relationship is many-to-many: one scene may require several
formula profiles, and one formula may support many scenes. This index is deliberately
separate from the Stage 1 sampling catalog, so loading it cannot change Guided-mode
scene selection, deduplication, labels, or student-facing copy.

`experiment_design_patterns.json` defines 15 reviewed experiment-design paradigms,
including forward visualization, parameter sweeps, controlled comparisons, inverse
inference, transient/frequency response, model breakdown, and optimization. Every
formula profile declares which paradigms are applicable. EMVR uses this coverage
matrix to generate methods for the selected formulas.

## Runtime rules

1. Stage 1 formula and method proposals must retain concept, formula and page provenance. The user confirms the formulas and experiment direction.
2. Course mapping must return cataloged concepts with lecture and page references.
3. Theory selection must return only formula records from the catalog.
4. Any uncataloged ECE329 claim requires a catalog/source update or an explicit user-provided source.
5. The workflow may guide the student to choose among grounded possibilities, but it must not invent course content to fill a gap.
