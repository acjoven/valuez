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

### Small merge fixtures — `done`
Two maps of the same gas, small enough to read in full: thermodynamics (12
concepts) and kinetic theory (9), from two chapters of the Feynman Lectures.
They share four names, three of them with different definitions, so the merge,
traversal, brief, and discovery docs can show a join end to end. Builder
`examples/merge_demo.py`; canonical `ontologies/thermodynamics.json` and
`ontologies/kinetic_theory.json`.

### Worked corpora — two large maps — `done`
Two curated maps at a realistic size, as test material for the features below:
Kant's critical philosophy across the three Critiques (builder
`examples/kant_ontology.py`; canonical `ontologies/kant.json`) and Kierkegaard's
authorship (builder `examples/kierkegaard_ontology.py`; canonical
`ontologies/kierkegaard.json`). The second deliberately shares nine node
**names** with the first (`MERGE_ANCHORS`). They are test material, not a
canon; see the note in [`README.md`](README.md#worked-corpora-two-large-maps).

### Ontology merge — fold many files into one universe — `done`
`valuez.merge_ontologies` imports multiple exported maps into a single connected
graph by keying on concept **name**, joining common nodes so every edge from
either source attaches to the one shared node. It resolves collisions by policy
(`first` / `last` / `raise`) and reports clean matches (`Volume` in the gas
maps) vs genuine semantic collisions (`Temperature`, `Pressure`,
`InternalEnergy`) whose fields differ between sources. Now also supports
**curated `aliases`** (join differently-named nodes like `IdealGas` =
`PerfectGas`, rewriting edge endpoints), **per-node provenance**
(`node_sources`), and the **cross-source bridges** (`MergeResult.bridges()`).
API in `valuez/merge.py`; worked runs in `examples/merge_demo.py` (small) and
`examples/merge_universe.py` (the two large maps); design note:
[`docs/merge.md`](docs/merge.md).

---

## Active knowledge — learn, massage ideas, create understanding

The platform is strong at *capture and structure*; this track makes it a place to
**learn from**, **work new ideas in**, and **derive new understanding**. Items are
ordered by dependency — each unlocks the next. Two invariants hold throughout:
derived/suggested items still carry a `Reference`, and meaning-bearing content
enters the canonical graph only through a human-reviewed path.

### 1. Merge alignment — `in progress`
Join concepts that mean the same thing, not just spell the same.

**Shipped (this slice):** curated `aliases` on `merge_ontologies`
(`[["IdealGas", "PerfectGas"]]` or `{"PerfectGas": "IdealGas"}`) fold
differently-named nodes to one canonical name and rewrite edge endpoints, so
alias-different subgraphs join too; the report lists `aliases_applied`. Design:
[`docs/merge.md`](docs/merge.md). Worked runs: `examples/merge_demo.py`, and
`examples/merge_universe.py` at scale.

**Next:** meaning-based *candidate* alignment (embeddings → suggested
`closeMatch`, human-approved into `aliases`), overlapping the Tier-4
`owl:sameAs` / SKOS angle. Design note: *to be written* (`docs/alignment.md`).

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

### 3. Concept briefs / `explain(node)` — `done`
Assemble a readable page for any node — definition, citations, immediate
relations, supporting arguments — so the graph becomes something you can *read*
and learn from. `valuez.explain(values, name)` returns a `Brief` (Markdown /
dict), with `.explain()` on `Reading`, `ValueRepository`, and `MergeResult`.
Claims and arguments attach by asserted edge or, labelled as such, by whole-word
*mention* of the concept name. Design: [`docs/briefs.md`](docs/briefs.md).
Worked run: `examples/concept_brief.py`.

### 4. Reasoning: inference + tension detection — `in progress`
Generalize `reasoning.py`'s transitive closures into typed forward-chaining rules
that emit *derived* (provenance-tagged) relations/propositions; add contradiction,
gap/open-question, and Dung-style argument acceptability detection.

**Shipped (this slice):** `valuez.analyze` — transitivity of the strict-order
predicates, symmetry of `contrasts-with` / `contradicts`, instantiation
inheritance along `is-a`; tensions (cycles, predicate clashes, conflicting
truth-values); gaps (dangling / isolated / undefined / ungrounded / open
questions / missing premises); Dung *grounded* status under `attacks`. Derived
edges are returned, not inserted, each with a `Reference` naming the rule and
the asserted ids it rested on. Design: [`docs/analysis.md`](docs/analysis.md).
Worked run: `examples/analysis_demo.py`. `.analyze()` on `Reading`,
`ValueRepository`, and `MergeResult`. The primitive helpers in
`valuez.reasoning` are unchanged.

**Next:** derived propositions; user-authored rules; preferred/stable Dung
semantics and bipolar `supports`; writing approved derivations back through the
review path.

### 5. Cross-universe discovery & synthesis — `in progress`
Turn a merged universe into insight: path-based discovery of *unexpected*
connections between concepts from different sources (needs (2)), thematic
clustering, and proposing new bridging concepts. Depends on (2) and (4).

**This slice:** exclusive-to-exclusive shortest paths that only exist because
a merge joined the maps (`valuez.discover` / `MergeResult.discover`). A
crossing is an undirected walk from a node exclusive to source A to a node
exclusive to source B that passes through at least one join point; joins
include alias-made ones (item 1). `MergeResult.bridges()` lists the edges
incident to a join point — the seam the crossings run through. Design:
[`docs/discovery.md`](docs/discovery.md). Worked runs:
`examples/merge_demo.py`, and `examples/discovery_demo.py` at scale.

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
