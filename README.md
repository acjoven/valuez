# valuez

**A traceable semantic exploration platform for building ground-truthed abstract concepts.**

`valuez` is an object-oriented Python library for formalizing knowledge — whether
that's engineering data, a controlled vocabulary, or an entire school of
philosophy — as a network of typed, **ground-truthable** values. Every value,
from a single number to a metaphysical universal, can carry a
[`Reference`](valuez/values.py) back to the source it came from, so the resulting
model is auditable rather than asserted.

It is built on top of [`dots`](../dots) (a sibling JSON storage / query / graph
toolkit): domain objects stay pure Python, while `dots` provides persistence and
interactive graph visualization.

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
  `dots` JSON storage and a collection of relations renders straight to an
  interactive graph.
- **Structural reasoning.** Transitive closure, cycle detection, and acyclicity
  checks over any predicate (`is-a`, `part-of`, `grounds`, …).
- **Ergonomic authoring.** The [`Reading`](valuez/reading.py) session lets you
  build an ontology *as you read* — cite a passage once, reuse concepts by name,
  and get eager validation at the point of entry.

---

## Installation

`valuez` targets Python 3.12+. It depends on the sibling `dots` repository, which
is installed editable (it is not published to PyPI).

```bash
# from the valuez repo root
python3 -m venv .venv
source .venv/bin/activate

pip install -e ../dots            # sibling storage/query/graph toolkit
pip install -r requirements.txt   # pint (units) + pytest
```

`valuez` itself is a plain package on the import path; the examples add the repo
root to `sys.path`, or you can `pip install -e .`-style by running from the root.
See [`AGENTS.md`](AGENTS.md) for environment notes and the exact test/lint
commands.

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
`from_dict()` so it persists through `dots` unchanged.

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
| **Reasoning** | `valuez.reasoning` | Transitive closure, inferred edges, cycle detection, acyclicity over any predicate. |
| **Authoring** | `Reading` / `OntologyBuilder` | Fluent, validating session for building ontologies as you read. |
| **Units** | `valuez.units` | pint integration; validates unit strings, optional `Quantity` conversion (degrades gracefully without pint). |

---

## Persistence & visualization

[`ValueRepository`](valuez/repository.py) is an OOP cover over the functional
`dots` storage/query/graph layer:

```python
from valuez import Scalar, Reference
from valuez.repository import ValueRepository

repo = ValueRepository(data_dir="data/store")
repo.add_value(Scalar(304.0, unit="W/m/K", label="k_ss",
                      reference=Reference("Incropera, Table A.1")))

repo.query("[?kind=='scalar'].label")          # JMESPath over stored docs
repo.to_graph_html("graph.html")               # interactive visualization
```

### Canonical ontology files

For sharing a model in git, export the whole store to one deterministic,
diff-friendly JSON file and re-hydrate it later:

```python
repo.export_ontology("ontologies/kant.json")           # sorted, stable-keyed
repo = ValueRepository.from_ontology("ontologies/kant.json")
```

The committed `ontologies/*.json` files are the source of truth; the expanded
per-document `dots` store is a regenerable local cache (see
[`ontologies/README.md`](ontologies/README.md)).

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
- **`kant_ontology.py`** — a large curated ontology of Kant's critical philosophy
  (~134 concepts, ~242 relations) using the lower-level API.
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
- **Content & knowledge graphs** — Kant ontology (`done`), Kierkegaard
  (`in progress`), and a near-term **ontology merge** to fold multiple maps into
  one universe (`planned`).
- **Interoperability** — Tier 4 standards export/import (RDF/OWL, SKOS, PROV,
  nanopublications; `design sketch`).

---

## Repository layout

```
valuez/        # the library (values, qualitative, semantic, metaphysics,
               #   dataset, function, reasoning, reading, units, repository)
examples/      # runnable, source-backed worked examples
ontologies/    # canonical single-file ontology exports (committed source of truth)
docs/          # design notes (Tier-3 LLM assist, Tier-4 interoperability)
tests/         # pytest suite
ROADMAP.md     # the living roadmap (source of truth; README links to it)
```
