# Roadmap

The living roadmap for `valuez`. This file is the source of truth; `README.md`
carries only a short teaser that links here, and each non-trivial item links to a
deep-dive design note under [`docs/`](docs/).

**Status legend:** `done` · `in progress` · `planned` · `design sketch` · `wont-do`

**How this roadmap works**

- Detail lives in exactly one place: `README.md` → `ROADMAP.md` → `docs/<item>.md`.
- Flip an item's status in the *same* PR that changes reality (e.g. `planned → done`
  when it ships) so the roadmap can't drift from the code.
- No calendar estimates — items are ordered by dependency and priority, not dates.
- Each item may link a tracking issue/PR for the interactive execution state.

## Guiding principles

- **Automate mechanics aggressively, automate content only as reviewable
  suggestions.** Scaffolding (ids, validation, provenance) should be automatic;
  meaning-bearing content enters the graph only through a human-reviewed path.
- **Everything is ground-truthed.** Every value/relation carries a `Reference`;
  maps stay small and reviewable in git.

---

## Authoring automation (Tiers 1–3)

### Tier 1 — fluent authoring — `done`
`Reading` / `OntologyBuilder`: citation context, create-or-reuse concepts, eager
validation, deterministic ids, one-call persistence/visualization.

### Tier 2 — text-ingestion hooks — `planned`
Load a source text and turn selected spans into `Reference` locators; support
bulk import of triple tables. Bridges reading a text and authoring the graph
without hand-copying citations. Design note: *to be written* (`docs/text_ingestion.md`).

### Tier 3 — optional local-LLM assist — `design sketch`
A *suggestion-only* ollama extractor that proposes schema-validated, span-cited
candidates for human accept/edit/reject, entering the graph only through the
Tier-1 API. Design: [`docs/llm_assist.md`](docs/llm_assist.md).

---

## Content & knowledge graphs

### Kant ontology — `done`
Curated ontology of Kant's critical philosophy across the three Critiques.
Builder `examples/kant_ontology.py`; canonical `ontologies/kant.json`.

### Kierkegaard ontology — `in progress`
Companion ontology of Kierkegaard's existential authorship, deliberately sharing
node **names** with the Kant map (`MERGE_ANCHORS`) as fixtures for the merge
below. Builder `examples/kierkegaard_ontology.py`; canonical
`ontologies/kierkegaard.json`. Complete and in review; flip to `done` when it
merges.

### Ontology merge — fold many files into one universe — `planned`
**Near-term focus.** A merge function that imports multiple exported maps (e.g.
`kant.json` + `kierkegaard.json`) into a single graph by keying on concept
**name**, with a policy for resolving collisions — clean matches (`Philosopher`,
`PhilosophicalWork`) vs genuine semantic collisions (`Existence`, `Freedom`,
`God`, `Reason`, ...) that differ in definition and `ontological_status` between
sources. Design note: *to be written* (`docs/merge.md`). Tracking: *TBD*.

---

## Interoperability

### Tier 4 — standards export/import — `design sketch`
Optional export/import to RDF/OWL, JSON-LD, SKOS, W3C PROV, and nanopublications
(plus CSL/BIBFRAME for bibliography), so `valuez` maps join the wider
structured-knowledge ecosystem. Design:
[`docs/interoperability.md`](docs/interoperability.md).
