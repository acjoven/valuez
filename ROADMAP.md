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

### Kierkegaard ontology — `done`
Companion ontology of Kierkegaard's existential authorship, deliberately sharing
node **names** with the Kant map (`MERGE_ANCHORS`) as fixtures for the merge
below. Builder `examples/kierkegaard_ontology.py`; canonical
`ontologies/kierkegaard.json`.

### Ontology merge — fold many files into one universe — `done`
`valuez.merge_ontologies` imports multiple exported maps (e.g. `kant.json` +
`kierkegaard.json`) into a single connected graph by keying on concept **name**,
joining common nodes so every edge from either source attaches to the one shared
node. It resolves collisions by policy (`first` / `last` / `raise`) and reports
clean matches (`Philosopher`, `PhilosophicalWork`) vs genuine semantic collisions
(`Existence`, `Freedom`, `God`, `Reason`, ...) that differ in definition and
`ontological_status` between sources. API in `valuez/merge.py`; worked run in
`examples/merge_universe.py`; design note: [`docs/merge.md`](docs/merge.md).

---

## Active knowledge — learn, massage ideas, create understanding

The platform is strong at *capture and structure*; this track makes it a place to
**learn from**, **work new ideas in**, and **derive new understanding**. Items are
ordered by dependency — each unlocks the next. Two invariants hold throughout:
derived/suggested items still carry a `Reference`, and meaning-bearing content
enters the canonical graph only through a human-reviewed path.

### 1. Merge alignment — `planned`
Join concepts that mean the same thing, not just spell the same. Curated
`aliases` (`Soul` = `TheSelf`) and meaning-based *candidate* alignment
(embeddings → suggested `closeMatch`, human-approved into `aliases`), overlapping
the Tier-4 `owl:sameAs` / SKOS angle. Design note: *to be written*
(`docs/alignment.md`).

### 2. Graph traversal & path queries — `in progress`
A traversal API over the existing `networkx` graph: neighborhoods, shortest
paths, topic subgraphs, "how does A relate to B". The foundation the rest of this
track (and any UI) leans on.

**Shipped (this slice):** `valuez.Graph` — `neighborhood` / `neighbors` /
`incident`, `how` / `shortest_path` / `paths`, `topic` / `subgraph`, plus
`.graph()` on `Reading`, `ValueRepository`, and `MergeResult`. Design:
[`docs/traversal.md`](docs/traversal.md). Worked run:
`examples/traversal_demo.py`.

**Next:** weighted paths (by `strength`), argument-map traversal.

### 3. Concept briefs / `explain(node)` — `planned`
Assemble a readable page for any node — definition, citations (`bibliography()`),
immediate relations, supporting arguments — so the graph becomes something you
can *read* and learn from. Depends on (2).

### 4. Reasoning: inference + tension detection — `planned`
Generalize `reasoning.py`'s transitive closures into typed forward-chaining rules
that emit *derived* (provenance-tagged) relations/propositions; add contradiction,
gap/open-question, and Dung-style argument acceptability detection. This is the
core that powers "massage ideas" and "create understanding".

### 5. Cross-universe discovery & synthesis — `in progress`
Turn a merged universe into insight: path-based discovery of *unexpected*
connections between concepts from different sources (needs (2)), thematic
clustering, and proposing new bridging concepts. Depends on (2) and (4).

**This slice:** exclusive-to-exclusive shortest paths that only exist because
a merge joined the maps (`valuez.discover` / `MergeResult.discover`). A
crossing is an undirected walk from a node exclusive to source A to a node
exclusive to source B that passes through at least one join point. Design:
[`docs/discovery.md`](docs/discovery.md). Worked run:
`examples/discovery_demo.py`.

**Next:** thematic clustering of exclusive neighborhoods; proposing new
bridging concepts (synthesis; needs (4) to score candidates).

### 6. Learning workflows — `planned`
Study/recall (flashcards from definitions and propositions with spaced
repetition) and guided reading paths (topological order over
`presupposes` / `requires` / `grounds`). Depends on (2)–(3).

### 7. Generative assist (Tier 3) — `design sketch`
Suggestion-only local-LLM proposals over a subgraph (new relations / propositions
/ questions) for human accept/edit/reject — the creativity amplifier, gated by the
review path. Tracked under *Authoring automation* above; sequenced last here.

---

## Interoperability

### Tier 4 — standards export/import — `design sketch`
Optional export/import to RDF/OWL, JSON-LD, SKOS, W3C PROV, and nanopublications
(plus CSL/BIBFRAME for bibliography), so `valuez` maps join the wider
structured-knowledge ecosystem. Design:
[`docs/interoperability.md`](docs/interoperability.md).
