# valuez

**A traceable semantic exploration platform for building ground-truthed abstract concepts.**

`valuez` is an object-oriented Python library for formalizing knowledge — whether
that's engineering data, a controlled vocabulary, or an entire school of
philosophy — as a network of typed, **ground-truthable** values. Every value,
from a single number to a metaphysical universal, can carry a
[`Reference`](valuez/values.py) back to the source it came from, so the resulting
model is auditable rather than asserted.

It is built on top of [`dotz`](https://github.com/acjoven/dotz) (a companion
JSON storage / query / graph toolkit): domain objects stay pure Python, while
`dotz` provides persistence and interactive graph visualization.

License: [MIT](LICENSE)

---

## Why valuez

- **Everything is traceable.** Any value can be attached to a `Reference`
  (source, locator, confidence, timestamp, metadata), so a model can be
  ground-truthed and audited.
- **A rich, typed value system.** Quantitative (`Scalar`, `Range`, `DataSet`,
  `Function`), qualitative (`Nominal`, `Ordinal`, `Boolean`, `Textual`),
  semantic (`Concept`, `Relation`, `Proposition`, `Argument`), and metaphysical
  (`Individual`, `Universal`, `Instantiation`) primitives share one base class
  and serialize uniformly.
- **Persistence & visualization for free.** Every value round-trips through
  `dotz` JSON storage and a collection of relations renders straight to an
  interactive graph.
- **Structural reasoning.** Transitive closure, cycle detection, and acyclicity
  checks over any predicate (`is-a`, `part-of`, `grounds`, …); `analyze()` runs
  those as typed rules and adds clashes, gaps, and Dung argument status.
- **Graph traversal.** Neighborhoods, shortest paths, topic subgraphs, and
  "how does A relate to B" over the relation graph (`valuez.Graph`).
- **Readable briefs.** `explain(node)` assembles one node's definition,
  relations, claims, arguments, and sources into a Markdown page.
- **Ergonomic authoring.** The [`Reading`](valuez/reading.py) session lets you
  build an ontology *as you read* — cite a passage once, reuse concepts by name,
  and get eager validation at the point of entry.

---

## Installation

`valuez` targets Python 3.12+. Neither `valuez` nor its one non-PyPI dependency,
[`dotz`](https://github.com/acjoven/dotz), is published to PyPI yet, so install
from a clone:

```bash
git clone https://github.com/acjoven/valuez.git
cd valuez
python3 -m venv .venv
source .venv/bin/activate

pip install "dotz @ git+https://github.com/acjoven/dotz.git"   # storage/query/graph toolkit
pip install -r requirements.txt                                # pint, pybtex, pytest

python -m pytest                       # check the install
python examples/reading_session.py     # run a first example
```

`valuez` is not packaged yet: run Python from the repo root so `import valuez`
resolves (the scripts under `examples/` add the repo root to `sys.path`
themselves, so they run from anywhere).

To work on `dotz` and `valuez` together, clone `dotz` next to `valuez` and
install it editable instead (`pip install -e ../dotz`).
[`scripts/setup_env.sh`](scripts/setup_env.sh) automates that layout; see
[`AGENTS.md`](AGENTS.md) for environment notes and the exact test/lint commands.

---

## Quickstart — build an ontology as you read

The fastest way in is the [`Reading`](valuez/reading.py) session (aliased
`OntologyBuilder`). It handles ids, de-duplication, provenance, and validation so
you can concentrate on the text:

```python
from valuez import Reading, Vocabulary

PREDICATES = Vocabulary("preds", ["is-a", "is-form-of", "produces", "requires", "instantiates"])

book = Reading(source="Kant, Critique of Pure Reason", predicates=PREDICATES, id_prefix="cpr_")

with book.at("A22/B36"):                      # cite the passage once…
    book.universal("Space", "Pure a priori form of outer intuition.")
    book.universal("Intuition", "Immediate, singular representation.")
    book.relate("Space", "is-form-of", "Intuition")   # both endpoints checked eagerly
    book.claim("Space and time are pure a priori forms of intuition.", truth_value=True)

with book.at("A51/B75"):
    book.universal("Understanding")
    book.universal("Concept")
    book.relate("Understanding", "produces", "Concept")

book.check()                                   # referential-integrity sweep
book.export("ontologies/my_kant.json")         # canonical single-file artifact
book.render("kant.html", include_inferred="is-a")   # interactive graph
```

Everything created inside a `with book.at(...)` block automatically inherits that
`Reference`, so provenance rides along with no extra typing. Declaring the same
concept twice returns the same node; an unknown relation endpoint or an
out-of-vocabulary predicate raises immediately, on the line that introduced it.

The lower-level API (constructing `Concept`/`Relation`/… directly) remains fully
available when you want explicit control — see `examples/kant_ontology.py`.

---

## The value system

Every type below subclasses [`Value`](valuez/values.py): it has a stable `id`, an
optional `label` and `Reference`, a `kind` discriminator, and `to_dict()` /
`from_dict()` so it persists through `dotz` unchanged.

| Layer | Types | Purpose |
| --- | --- | --- |
| **Provenance** | `Reference` | Ground-truth pointer (source, locator, confidence, metadata) with optional BibTeX fields (key, entry type, authors). |
| | `ReferenceRepository` | Keyed source manager: collect cited sources (`from_values`), import/export `.bib`, render bibliographies (via optional `pybtex`). |
| **Quantitative** | `Scalar`, `Range` | A number / a closed interval `[low, high]` with optional `nominal`; pint-backed units. |
| | `DataSet` | A unit-coherent collection of `Scalar`/`Range` with interval-aware aggregates. |
| | `Sample`, `Function` | Input→output observations and an n-D function with interpolation / nearest-neighbor / sectioning. |
| **Qualitative** | `Vocabulary` | A ground-truthable controlled set of terms (ordered or nominal). |
| | `Nominal`, `Ordinal` | An unordered / ranked category validated against a `Vocabulary`. |
| | `Boolean`, `Textual` | A binary flag / free-form text. |
| **Semantic** | `Concept` | A named node in a semantic graph. |
| | `Relation` | A typed, directed edge (`source --predicate--> target`) with optional modality/strength. |
| | `Proposition`, `Argument` | A reified truth-apt claim / premises→conclusion (Dung-style support/attack). |
| **Metaphysics** | `Individual`, `Universal` | A particular / a kind, each with an optional `ontological_status`. |
| | `Instantiation` | A typed `Individual --instantiates--> Universal` edge. |
| **Reasoning** | `valuez.reasoning` / `analyze` | Transitive closure and cycles; typed inference, tensions, gaps, Dung grounded status. |
| **Traversal** | `valuez.Graph` | Neighborhoods, shortest paths, topic subgraphs, "how does A relate to B". |
| **Briefs** | `valuez.explain` / `Brief` | A readable page per node: definition, relations, claims, arguments, sources. |
| **Authoring** | `Reading` / `OntologyBuilder` | Fluent, validating session for building ontologies as you read. |
| **Units** | `valuez.units` | pint integration; validates unit strings, optional `Quantity` conversion (degrades gracefully without pint). |

---

## Persistence & visualization

[`ValueRepository`](valuez/repository.py) is an OOP cover over the functional
`dotz` storage/query/graph layer:

```python
from valuez import Scalar, Reference
from valuez.repository import ValueRepository

repo = ValueRepository(data_dir="data/store")
repo.add_value(Scalar(304.0, unit="W/m/K", label="k_ss",
                      reference=Reference("Incropera, Table A.1")))

repo.query("[?kind=='scalar'].label")          # JMESPath over stored docs
repo.to_graph_html("graph.html")               # interactive visualization
repo.graph().how("Space", "Intuition")         # walk the relation graph
```

### Canonical ontology files

For sharing a model in git, export the whole store to one deterministic,
diff-friendly JSON file and re-hydrate it later:

```python
repo.export_ontology("ontologies/kant.json")           # sorted, stable-keyed
repo = ValueRepository.from_ontology("ontologies/kant.json")
```

The committed `ontologies/*.json` files are the source of truth; the expanded
per-document `dotz` store is a regenerable local cache (see
[`ontologies/README.md`](ontologies/README.md)).

### Merging ontologies into one universe

Fold several maps into a single connected graph. Because edges reference their
endpoints **by name**, `merge_ontologies` joins same-named nodes so every edge
from either source attaches to the one shared node — the graphs stitch together
at the concepts they have in common:

```python
from valuez import merge_ontologies

res = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"])
print(res.report.summary())        # join points, semantic collisions, edge dedup
res.export("ontologies/universe.json")   # optional: a derived, regenerable map
```

Conflicting definitions are resolved by policy (`first` / `last` / `raise`) and
reported. Concepts the two traditions name differently join through curated
aliases, and `bridges()` lists the edges that now cross the seam:

```python
aligned = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"],
                           aliases=[["TheSelf", "Soul"]])   # or {"Soul": "TheSelf"}
aligned.report.aliases_applied       # {"TheSelf": ["Soul", "TheSelf"]}
aligned.bridges()                    # edges incident to a join point
```

See [`docs/merge.md`](docs/merge.md) and `examples/merge_universe.py`.

### Walking the graph

Once a map is stored, `valuez.Graph` answers neighborhood / path / topic
questions over concept **name** (the same identity edges already use):

```python
from valuez import Graph

g = Graph.from_ontology("ontologies/kant.json")
print(g.how("Space", "Intuition"))          # Space -is-form-of-> Intuition
print(g.neighborhood("Freedom", hops=1).nodes)
g.topic("Freedom", hops=1).visualize("freedom.html")
```

`Reading.graph()`, `ValueRepository.graph()`, and `MergeResult.graph()` return
the same object. See [`docs/traversal.md`](docs/traversal.md).

### Reading a node

`explain(node)` turns one node into a page — definition, every incident relation
with its citation, the claims and arguments that bear on it, and the sources
behind all of that:

```python
from valuez import explain, merge_ontologies

universe = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"])
print(universe.explain("Freedom").to_markdown())   # Kant and Kierkegaard on one page
```

`Reading.explain()` and `ValueRepository.explain()` do the same for a session or
a store. See [`docs/briefs.md`](docs/briefs.md).

### Inference and tensions

`analyze()` runs the structural-order helpers as typed rules and reports what
they find -- derived edges (returned, not inserted), illicit cycles and
predicate clashes, unfinished gaps, and Dung grounded status of arguments:

```python
from valuez import analyze

report = analyze(book.values())            # or repo.analyze() / merge_result.analyze()
print(report.summary())
for edge in report.relations:              # inferred, provenance-tagged
    print(edge.source, edge.predicate, edge.target)
```

See [`docs/analysis.md`](docs/analysis.md).

### Cross-universe discovery

After a merge, `discover` finds shortest paths from a concept that lived in
only one source to a concept that lived only in another — walks that do not
exist in either ontology alone, because they pass through a join point the
merge created:

```python
from valuez import discover, merge_ontologies

res = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"])
found = res.discover(cutoff=2)
print(found.summary())
# TranscendentalIdealism [kant] ~ Freedom ~ Anxiety [kierkegaard]
```

See [`docs/discovery.md`](docs/discovery.md) and `examples/discovery_demo.py`.

### Managing sources (BibTeX)

A `Reference` can carry a full bibliographic record, and `ReferenceRepository`
manages sources by citation key so many values can share one keyed source
instead of duplicating a citation string:

```python
from valuez import ReferenceRepository, Scalar

refs = ReferenceRepository()
refs.import_bibtex("sources.bib")                 # or a BibTeX string
h = Scalar(25.0, unit="W/m^2/K", reference=refs.reference("incropera2007"))

refs.export_bibtex("out.bib")                     # write the library back out
print(refs.format_bibliography()["incropera2007"])  # formatted citation
```

To collect the sources actually *cited* across an ontology (rather than track
them by hand), build a repository straight from the values:

```python
cited = ReferenceRepository.from_values(reading.values())  # or a list of values
cited = reading.bibliography()                             # equivalent shortcut
cited = value_repo.bibliography()                          # from a stored ontology
cited.export_bibtex("cited.bib")
```

BibTeX I/O and formatting use the optional `pybtex` dependency; `valuez` core
works without it (only these operations require it).

---

## Examples

Runnable, source-backed examples live in [`examples/`](examples/README.md):

- **`reading_session.py`** — build a first-Critique ontology via the fluent
  `Reading` API (the ergonomic entry point).
- **`kant_ontology.py`** / **`kierkegaard_ontology.py`** — two large curated
  ontologies (Kant's critical philosophy and Kierkegaard's existential
  authorship) built to the same shape so they can be merged.
- **`merge_universe.py`** — join those two maps into one universe with
  `merge_ontologies`, reporting the shared nodes that stitch the graphs together.
- **`traversal_demo.py`** — walk a stored map: neighborhoods, "how does A
  relate to B", topic subgraphs (`valuez.Graph`).
- **`concept_brief.py`** — read a node: `explain("Freedom")` on Kant alone and
  on the merged Kant + Kierkegaard universe, written as Markdown.
- **`analysis_demo.py`** — infer, flag tensions, list gaps, score arguments
  (`valuez.analyze`).
- **`discovery_demo.py`** — unexpected paths created by that merge: Kant-only
  concepts now a short walk from Kierkegaard-only concepts (`valuez.discover`).
- **`heat_transfer_cooling.py`** — a worked engineering problem: source-backed
  heat-transfer coefficients driving a lumped-capacitance cooling calculation.
- **`dataset_htc.py`** / **`empirical_functions.py`** — `DataSet` and
  `Sample`/`Function` over real measured data.
- **`philosophy_framework.py`** / **`metaphysics_framework.py`** — the semantic
  and metaphysics layers (arguments, instantiation, structural reasoning).

```bash
python examples/reading_session.py     # writes JSON + an interactive graph
```

---

## Development

```bash
.venv/bin/python -m pytest                                  # test suite
.venv/bin/python -m py_compile valuez/*.py examples/*.py tests/*.py   # syntax check (no linter configured)
```

See [`AGENTS.md`](AGENTS.md) for the authoritative dev/test/run notes.

---

## Roadmap

The full, living roadmap lives in [`ROADMAP.md`](ROADMAP.md). In brief:

- **Authoring automation** — Tier 1 fluent authoring (`done`), Tier 2
  text-ingestion hooks (`planned`), Tier 3 optional local-LLM assist
  (`design sketch`), following the principle *automate mechanics aggressively,
  automate content only as reviewable suggestions*.
- **Content & knowledge graphs** — Kant and Kierkegaard ontologies (`done`), and
  an **ontology merge** that folds multiple maps into one universe by joining
  common nodes (`done`; `valuez.merge_ontologies`, see
  [`docs/merge.md`](docs/merge.md)).
- **Active knowledge** — merge alignment (`in progress`; curated `aliases` on
  `merge_ontologies`), graph traversal (`in progress`; `valuez.Graph`, see
  [`docs/traversal.md`](docs/traversal.md)), concept briefs (`done`;
  `valuez.explain`, see [`docs/briefs.md`](docs/briefs.md)), inference +
  tension detection (`in progress`; `valuez.analyze`, see
  [`docs/analysis.md`](docs/analysis.md)), and cross-universe discovery
  (`in progress`; `valuez.discover`, see [`docs/discovery.md`](docs/discovery.md)).
- **Interoperability** — Tier 4 standards export/import (RDF/OWL, SKOS, PROV,
  nanopublications; `design sketch`).

---

## Repository layout

```
valuez/        # the library (values, qualitative, semantic, metaphysics,
               #   dataset, function, reasoning, analysis, traversal, briefs,
               #   discovery, reading, units, repository)
examples/      # runnable, source-backed worked examples
ontologies/    # canonical single-file ontology exports (committed source of truth)
docs/          # design notes (traversal, briefs, analysis, discovery, merge,
               #   Tier-3 LLM assist, Tier-4 interop)
tests/         # pytest suite
ROADMAP.md     # the living roadmap (source of truth; README links to it)
```
