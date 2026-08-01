# Examples

## `heat_transfer_cooling.py` — natural-convection cooling of stainless steel

A worked engineering example that uses the valuez `Scalar` / `Range` / `Reference`
primitives to hold **source-backed** data, then computes how a hot stainless-steel
part cools in still room air.

### Problem

A solid AISI 304 stainless-steel cube (50 mm side) starts at **300 °C** and cools
in still room air at **25 °C** by **natural (free) convection**. We want the
cooling rate and how long it takes to cool down.

### Ground-truthed inputs

Every input is a `Scalar` or `Range` carrying a `Reference` so it can be traced
back to its source.

Overall / natural-convection heat-transfer coefficient of air, `h` (W/m²·K):

| Value | Source |
| --- | --- |
| 2 – 25 | Incropera & DeWitt, *Fundamentals of Heat and Mass Transfer* (6e), Table 1.1 (free convection, gases) |
| 2.5 – 25 | Standard heat-transfer tables (Air, free convection) |
| 3 – 25 | HVAC Systems Encyclopedia (ingener.by), natural convection, gases |
| ~7 | COMSOL paper — representative computed `h` for natural convection (laminar) |

AISI 304 thermal properties:

| Property | Value | Source |
| --- | --- | --- |
| Density ρ | 8000 kg/m³ | MatWeb 304 SS (8.00 g/cc); thepipingmart SS304 |
| Specific heat cₚ | 500 J/kg·K | MatWeb 304 SS (0–100 °C); AZoM Grade 304 |
| Thermal conductivity k | 16.2 W/m·K | MatWeb 304 SS (0–100 °C) |

### Model

Lumped-capacitance cooling (Newton's law of cooling), valid when the Biot number
`Bi = h·Lc/k < 0.1`:

```
tau  = rho * Lc * cp / h            # cooling time constant [s]
T(t) = T_inf + (T0 - T_inf) * exp(-t / tau)
|dT/dt|_0 = (T0 - T_inf) / tau      # initial cooling rate
Lc   = V / A  (= L/6 for a cube)
```

Radiation is neglected (a reasonable first cut; near 300 °C it would add a few
W/m²·K in parallel and speed cooling somewhat). The `h` **range** is propagated
into a **range** of cooling rates and time constants.

### Run

```bash
# dots (sibling repo) must be importable, e.g.:  pip install -e ../dots
python examples/heat_transfer_cooling.py
```

The script prints an engineering report, persists all inputs and derived values
through `dots` storage, and writes a provenance graph (`provenance.html`) that
links each value to its source. Output goes to `$VALUEZ_EXAMPLE_OUT`
(default: a `valuez_heat_transfer/` folder in your temp directory).

### Representative output (Bi ≈ 0.001–0.013, lumped model valid)

```
Initial cooling rate |dT/dt|_0 : 0.99 to 12.38 K/min   (h = 2 to 25 W/m^2K)
Time constant tau              : 22.2 to 277.8 min
Time to reach 100 degC         : 29 to 361 min
Time to reach 50 degC          : 53 to 666 min
```

## `philosophy_framework.py` — a philosophical framework (Gettier problem)

Shows that the semantic + argument primitives can model a **philosophical
framework** as a traceable graph, not just an engineering dataset.

It encodes the classical analysis of knowledge and Gettier's challenge:

- `Concept`s — `Knowledge`, `JustifiedTrueBelief`, `Belief`, `Truth`, `Justification`.
- `Relation`s over a controlled **predicate vocabulary**
  (`defines`, `presupposes`, `attacks`, ...) with qualifiers — a `modality`
  (`necessary`, `defeasible`, ...) and a `strength` in `[0, 1]`. E.g.
  `JustifiedTrueBelief --presupposes [necessary]--> Justification`.
- `Proposition`s — reified, truth-apt claims (P1, P2, conclusion), each cited.
- `Argument`s — premises ⇒ conclusion (Gettier's reductio; a no-false-lemmas
  rebuttal), with `scheme` labels.
- Argument-level `attacks` relations forming a small Dung-style network:
  `Gettier-Argument attacks JustifiedTrueBelief`, and
  `No-False-Lemmas attacks Gettier-Argument`.

Every claim/relation is ground-truthed via `Reference` (Plato's *Theaetetus*,
Gettier 1963, Clark 1963).

### Run

```bash
python examples/philosophy_framework.py
```

The script prints the framework, persists all values through `dots`, and writes
an interactive **argument map** (`argument_map.html`) wiring premises →
arguments → conclusions plus the attack relations. Output goes to
`$VALUEZ_EXAMPLE_OUT` (default: a `valuez_philosophy/` folder in your temp dir).

## `metaphysics_framework.py` — particulars, universals, and structural orders

Shows the **metaphysics slice**: the particular/universal distinction, a *typed*
instantiation relation, and the `reasoning` helper for structural orders.

It encodes a small ontology:

- `Universal`s (kinds/properties: `LivingThing`, `Animal`, `Mammal`, `Human`,
  `Colored`, `Red`, `Scarlet`) and `Individual`s (particulars: `Socrates`,
  `Plato`, `ThisApple`), each with an optional **`ontological_status`**
  (`concrete` / `abstract` / `fundamental`).
- `Instantiation` — a **typed** edge that enforces
  `Individual --instantiates--> Universal` (e.g. `Socrates instantiates Human`);
  passing a universal as the source (or an individual as the target) raises.
- `Relation`s over a controlled predicate vocabulary for the structural orders:
  `is-a` (kind subsumption), `part-of` (mereology), `grounds`
  (determinate ⇒ determinable).

It then uses `valuez.reasoning`:

- `infer_transitive` — derives the **transitive closure** of `is-a` and
  `part-of`, emitting *new* edges tagged `modality="inferred"` (e.g.
  `Human is-a LivingThing`, `Cell part-of Organism`).
- `is_acyclic` / `find_cycles` — checks that `grounds` (a strict order) has no
  cycles, then adds a deliberately illicit `Colored grounds Scarlet` edge to
  demonstrate **cycle detection**.

### Run

```bash
python examples/metaphysics_framework.py
```

The script prints the ontology and the inferred/checked results, persists all
values through `dots`, and writes an interactive **ontology graph**
(`ontology_graph.html`) with asserted plus inferred edges. Output goes to
`$VALUEZ_EXAMPLE_OUT` (default: a `valuez_metaphysics/` folder in your temp dir).

## `dataset_htc.py` — collecting related quantitative values with `DataSet`

Shows when a `DataSet` is worth more than a plain list. It compiles the
natural-convection heat-transfer coefficient of air, `h`, as reported across
several sources — a mix of `Scalar` and `Range` values in `W/(m²·K)`.

- **Invariants**: every member must be quantitative and share the one unit, so
  the aggregates are meaningful.
- **Interval-aware aggregates**: `min` / `max` / `mean` / `span` and
  `envelope()` treat a `Range` by its bounds; the envelope is the overall band
  across all sources.
- **Collection-level provenance**: the `DataSet` is itself a ground-truthed
  `Value`, so the whole compilation persists as a **single** `dots` document
  (one id) instead of loose rows.
- **List ergonomics**: iterate/index/slice it like a list; `grounded()` and
  `by_kind()` return sub-`DataSet`s.

### Run

```bash
python examples/dataset_htc.py
```

The script prints the member table and aggregates, then persists the whole set
as one document and reloads it (verifying the round-trip). Output goes to
`$VALUEZ_EXAMPLE_OUT` (default: a `valuez_dataset/` folder in your temp dir).

## `empirical_functions.py` — contextualizing data with `Function`

Shows the `Sample` / `Function` layer: a measured quantity captured together
with the *conditions* it was measured at, single- or multi-dimensional.

- **1-D** — molar heat capacity `cp(T)` of N₂ tabulated at several temperatures.
  Demonstrates linear `interpolate` / `__call__` between measured points (no
  extrapolation).
- **3-D** — catalytic reaction `conversion(T, P, space_velocity)`. Demonstrates
  `nearest(...)` and `at(...)` lookups, and `section(P=..., SV=...)` to project
  conversion vs. temperature at fixed conditions.

Each input coordinate and output is a ground-truthed `Scalar`/`Range` (a couple
of the conversion points are `Range`s to model measurement uncertainty), the
schema (variable names + per-axis units + output unit) is enforced on every
sample, and each whole function persists as a **single** `dots` document.

### Run

```bash
python examples/empirical_functions.py
```

Output goes to `$VALUEZ_EXAMPLE_OUT` (default: a `valuez_functions/` folder in
your temp dir).

## `reading_session.py` — build an ontology *as you read*

The ergonomic counterpart to `kant_ontology.py`. It reconstructs the epistemic
core of the first Critique (sensibility / understanding, space & time, the
categories, the Transcendental Deduction) using the Tier-1 authoring helper
`valuez.Reading` instead of the raw `Concept` / `Relation` API.

The point is to show how much scaffolding the session removes:

- `with book.at("A51/B75"):` cites a passage **once**; every concept, relation,
  and claim in the block inherits that `Reference` automatically.
- `book.universal(name, definition)` is **create-or-reuse** (declaring a term
  twice returns the same node and can enrich a missing definition).
- `book.relate(src, pred, tgt)` validates **eagerly** — both endpoints must be
  declared and the predicate must be in the controlled `Vocabulary` — so typos
  raise at the line that introduced them, not in a late integrity sweep.
- `book.instantiate(...)` enforces `Individual --instantiates--> Universal`.
- `book.check()`, `book.is_acyclic(...)`, `book.infer_transitive(...)`,
  `book.export(...)`, and `book.render(...)` cover validation, reasoning,
  persistence, and visualization in one call each.

### Run

```bash
python examples/reading_session.py
```

Writes `reading_session.json` and an interactive graph (with inferred `is-a`
edges overlaid) to `$VALUEZ_EXAMPLE_OUT` (default: a `valuez_reading/` folder in
your temp dir). For the optional, suggestion-only LLM tier that would feed
candidates into this same session, see [`docs/llm_assist.md`](../docs/llm_assist.md).

## `bibliography_demo.py` — manage sources as BibTeX

Shows `valuez.ReferenceRepository`: load a BibTeX library, ground several values
in a single **shared keyed source** (no duplicated citation strings), cite a
source inside a `Reading` session by key, then export the library back to `.bib`
and render a formatted bibliography. BibTeX I/O uses the optional `pybtex`
dependency.

### Run

```bash
python examples/bibliography_demo.py
```

Writes `sources.bib` to `$VALUEZ_EXAMPLE_OUT` (default: a `valuez_bibliography/`
folder in your temp dir).

## `kant_ontology.py` — the critical philosophy of Immanuel Kant

A larger **content** example: a curated ontology of Kant's system spanning the
three Critiques, built entirely from the semantic + metaphysics primitives.

- **Particulars** (`Individual`): Kant and his major works.
- **Universals** (`Universal`, ~134): faculties (sensibility / understanding /
  reason), representations (intuition / concept / category / idea), the full
  **table of categories** (four titles + twelve), phenomena vs. noumena, the
  ideas of reason (soul / cosmos / God), the four **antinomies** (with their
  paired **thesis / antithesis** claims) and four **paralogisms**, further
  sections of the Analytic (metaphysical deduction, schematism, principles,
  refutation of idealism), the moral concepts (categorical imperative and its
  four **formulas**, autonomy, good will, kingdom of ends, the **postulates**
  and the **highest good**), and the third-Critique concepts in depth
  (reflecting vs. determining judgment, the four **moments of taste**,
  mathematical / dynamical **sublime**, aesthetic idea, common sense, fine art,
  and **teleological judgment** / natural purpose / organism). Each carries an
  `ontological_status` (`transcendental` / `a priori` / `phenomenal` /
  `noumenal` / ...).
- **Instantiation**: typed `Individual --instantiates--> Universal` edges.
- **Relations** (~242) over a controlled vocabulary: `is-a`, `part-of`
  (structure of the Critiques), `contrasts-with` (Kant's dichotomies and the
  antinomic thesis/antithesis pairs), `formulation-of` (the CI formulas), plus
  `grounds` / `requires` / `produces` / `enables` / `presupposes` /
  `applies-to` / `addresses` / `is-form-of`, including cross-Critique bridges
  (e.g. transcendental idealism grounding freedom).
- **Propositions** (14 cited theses) and five **Arguments**: the Transcendental
  Deduction, the good-will argument, the resolution of the Third Antinomy, the
  moral argument for the postulates, and the deduction of taste.

The script checks **referential integrity** (every edge endpoint is a defined
node), reasons over the graph (transitive closure of `is-a`; acyclicity of the
strict orders), persists everything through `dots`, **exports the canonical
`ontologies/kant.json`**, and renders an interactive graph.

### Run

```bash
python examples/kant_ontology.py
```

`ontologies/kant.json` is the committed source-of-truth artifact; the rendered
`kant_ontology.html` / `kant_arguments.html` go to `$VALUEZ_EXAMPLE_OUT`
(default: a `valuez_kant/` folder in your temp dir).

## `kierkegaard_ontology.py` — the existential philosophy of Søren Kierkegaard

A second large **content** example, built to the exact same shape as
`kant_ontology.py` so the two can eventually be **merged** into one universe.

- **Particulars** (`Individual`, 22): Kierkegaard, his **pseudonymous personae**
  (Johannes de silentio, Johannes/Anti-Climacus, Vigilius Haufniensis, ...), his
  major **works**, and the exemplary **figures** (Abraham, Don Juan, Judge
  William).
- **Universals** (`Universal`, ~68): the three **stages of existence**
  (aesthetic / ethical / religious, plus Religiousness A/B), the **self as
  synthesis** (possibility/necessity, finitude/infinitude, temporality/eternity),
  **anxiety** and **despair**, **faith** and the **absolute paradox** (the god in
  time), subjectivity / truth / inwardness, and indirect communication. Each
  carries an `ontological_status` (`existential` / `theological` /
  `psychological` / `abstract`).
- **Instantiation**: typed `Individual --instantiates--> Universal` (personae are
  `Pseudonym`s, works are `PhilosophicalWork`s, figures are `Exemplar`s).
- **Relations** (~167) over a controlled vocabulary that is a **superset of the
  Kantian one** plus `authored-as`, `critiques`, `exemplifies`, `synthesizes`,
  and `leads-to` (the stage progression), alongside `is-a`, `part-of` (the self's
  synthesis), `contrasts-with` (Kierkegaard's dualities), `grounds`, `requires`,
  `presupposes`, `produces`, `addresses`, and `wrote`.
- **Propositions** (11 cited theses) and five **Arguments**: the teleological
  suspension of the ethical, subjectivity-is-truth, the self and despair, the
  case against the system, and the paradox and offense.

### Built for merging

This graph deliberately **reuses universal names** from `kant_ontology.py` so a
future *merge* has real overlap to resolve (`MERGE_ANCHORS` in the script):
`Philosopher` / `PhilosophicalWork` are clean matches, while `Existence`,
`Freedom`, `Possibility`, `Necessity`, `Reason`, `Understanding`, and `God` are
genuine **semantic collisions** — the same name with a different definition and
`ontological_status` in each system. The two files use disjoint id prefixes
(`kk_` vs `k_`), so a merge is forced to key on **name** and decide how to fold
colliding concepts.

### Run

```bash
python examples/kierkegaard_ontology.py
```

`ontologies/kierkegaard.json` is the committed source-of-truth artifact; the
rendered `kierkegaard_ontology.html` / `kierkegaard_arguments.html` go to
`$VALUEZ_EXAMPLE_OUT` (default: a `valuez_kierkegaard/` folder in your temp dir).
