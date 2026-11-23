# valuez

**A traceable semantic exploration platform for building ground-truthed abstract concepts.**

`valuez` is an object-oriented Python library for formalizing knowledge — whether
that's engineering data, a controlled vocabulary, or the ideas in a text — as a
network of typed, **ground-truthable** values. Every value, from a single number
to an abstract concept, can carry a [`Reference`](valuez/values.py) back to the
source it came from, so the resulting model is auditable rather than asserted.

It is built on top of [`dotz`](https://github.com/acjoven/dotz) (a companion
JSON storage / query / graph toolkit): domain objects stay pure Python, while
`dotz` provides persistence and interactive graph visualization.

License: [MIT](LICENSE)

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
pip install -e ".[dev]"                                        # valuez + pint, pybtex, pytest

python -m pytest                  # check the install
python examples/quickstart.py     # run a first example
```

`pip install -e ".[dev]"` installs `valuez` editable from [`pyproject.toml`](pyproject.toml),
so `import valuez` works from any directory. The `dev` extra pulls in the test
runner and the optional BibTeX backend; a leaner install is
`pip install -e .` (runtime only) or `pip install -e ".[bib]"`.

To work on `dotz` and `valuez` together, clone `dotz` next to `valuez` and
install it editable instead (`pip install -e ../dotz`).
[`scripts/setup_env.sh`](scripts/setup_env.sh) automates that layout; see
[`AGENTS.md`](AGENTS.md) for environment notes and the exact test/lint commands.

---

## Quickstart

A number that knows where it came from, and a small concept map built while
reading the same textbook:

```python
from valuez import Range, Reading, Reference, Vocabulary

TEXTBOOK = "Incropera & DeWitt, Fundamentals of Heat and Mass Transfer (6e)"

h = Range(2, 25, unit="W/(m^2*K)", label="h, free convection in gases",
          reference=Reference(TEXTBOOK, locator="Table 1.1"))

book = Reading(source=TEXTBOOK, predicates=Vocabulary("relations", ["is-a"]))

with book.at("Section 1.1"):                       # cite the passage once...
    book.concept("HeatTransfer", "Thermal energy in transit due to a temperature difference.")
    book.concept("Conduction", "Heat transfer across a stationary medium.")
    book.concept("Convection", "Heat transfer between a surface and a moving fluid.")
    book.concept("Radiation", "Energy emitted by a surface as electromagnetic waves.")
    for mode in ("Conduction", "Convection", "Radiation"):
        book.relate(mode, "is-a", "HeatTransfer")  # ...and it rides along on every item

with book.at("Section 1.2.2"):
    book.concept("FreeConvection", "Convection driven by buoyancy in the fluid.")
    book.concept("ForcedConvection", "Convection driven by external means such as a fan or pump.")
    book.relate("FreeConvection", "is-a", "Convection")
    book.relate("ForcedConvection", "is-a", "Convection")

print(book.get("FreeConvection").reference.locator)
# Section 1.2.2
print([(e.source, e.target) for e in book.infer_transitive("is-a")])
# [('ForcedConvection', 'HeatTransfer'), ('FreeConvection', 'HeatTransfer')]
print(book.graph().how("FreeConvection", "Radiation"))
# FreeConvection -is-a-> Convection -is-a-> HeatTransfer <-is-a- Radiation

book.render("heat_transfer.html")                  # interactive graph
book.export("heat_transfer.json")                  # the whole map as one diff-friendly JSON file
```

Three things happened without extra typing. Everything created inside a
`with book.at(...)` block inherited that citation. Declaring a concept twice
would have returned the same node. And a relation to an undeclared concept, or
with a predicate outside the vocabulary, would have raised on the line that
introduced it.

[`examples/quickstart.py`](examples/quickstart.py) is this snippet as a script.
The lower-level API (constructing `Concept` / `Relation` objects directly) is
there when you want explicit control; `examples/philosophy_framework.py` uses
it.

---

## What you can do with it

- **Hold sourced quantities** — `Scalar`, `Range`, `DataSet`, and `Function`,
  with pint-backed units.
- **Hold sourced ideas** — `Concept` and `Relation`, `Proposition` and
  `Argument`, and the `Individual` / `Universal` distinction, alongside
  categorical values checked against a `Vocabulary`.
- **Author as you read** — the [`Reading`](valuez/reading.py) session from the
  quickstart.
- **Store, query, and draw** — `ValueRepository` round-trips every value
  through `dotz` JSON storage and renders relations as an interactive graph.
- **Ask questions of a map** — `Graph` for neighborhoods and paths, `explain`
  for a readable page about one node, `analyze` for inferred edges, cycles,
  clashes, and gaps.
- **Join maps** — `merge_ontologies` stitches independently written maps
  together at the names they share, and `discover` lists the paths that only
  exist after the join.
- **Manage sources** — `ReferenceRepository` keeps citations in one
  BibTeX-backed place that many values point at.

[`docs/tour.md`](docs/tour.md) goes further: the full table of value types,
then persistence, merging, traversal, briefs, analysis, discovery, and source
management, each with code.

---

## Examples

Start with these six; each is self-contained and needs nothing beyond the
install:

1. [`quickstart.py`](examples/quickstart.py) — the snippet above.
2. [`heat_transfer_cooling.py`](examples/heat_transfer_cooling.py) — a worked
   engineering problem: sourced heat-transfer coefficients driving a cooling
   calculation, with the uncertainty carried through as a range.
3. [`philosophy_framework.py`](examples/philosophy_framework.py) — an argument
   map: the classical analysis of knowledge, Gettier's objection, and a reply.
4. [`metaphysics_framework.py`](examples/metaphysics_framework.py) — kinds and
   particulars, typed instantiation, inferred edges, and cycle detection.
5. [`bibliography_demo.py`](examples/bibliography_demo.py) — one BibTeX library
   shared across many values.
6. [`merge_demo.py`](examples/merge_demo.py) — two small maps of the same gas,
   one from thermodynamics and one from kinetic theory, joined at the four
   names they share. It shows where their definitions disagree and which paths
   exist only after the join.

The rest, one feature each, are described in
[`examples/README.md`](examples/README.md).

---

## Worked corpora: two large maps

Besides the two small maps `merge_demo.py` builds,
[`ontologies/`](ontologies/README.md) holds two large curated ones, one of
Kant's critical philosophy and one of Kierkegaard's authorship, each a few
hundred nodes and edges. They give the merge, traversal, brief, and discovery
features something realistically large to work on: two dense systems that use
the same words (`Freedom`, `Reason`, `Existence`) in different senses, which is
the hard case when joining maps.

They are test material, not a canon:

- Including an author is not an endorsement of their views, and leaving one out
  is not a judgment.
- The maps describe what the cited texts say. They are not claims by `valuez`
  about what is true.
- Nothing in the library is specific to philosophy. Maps of other traditions
  and fields are welcome.

You do not need them to learn the library. When you want them, the builders are
`examples/kant_ontology.py` and `examples/kierkegaard_ontology.py`, and
`merge_universe.py`, `discovery_demo.py`, and `concept_brief.py` run over the
two maps.

---

## Documentation

- [`docs/tour.md`](docs/tour.md) — the longer tour described above.
- [`docs/`](docs/) — one design note per feature.
- [`ROADMAP.md`](ROADMAP.md) — what is done, in progress, and planned.

---

## Development

```bash
.venv/bin/python -m pytest                                  # test suite
.venv/bin/python -m py_compile valuez/*.py examples/*.py tests/*.py   # syntax check (no linter configured)
```

See [`AGENTS.md`](AGENTS.md) for the authoritative dev/test/run notes.

---

## Repository layout

```
valuez/        # the library (values, qualitative, semantic, metaphysics,
               #   dataset, function, reasoning, analysis, traversal, briefs,
               #   discovery, reading, units, repository)
examples/      # runnable, source-backed worked examples
ontologies/    # canonical single-file ontology exports (committed source of truth)
docs/          # the tour, plus design notes (traversal, briefs, analysis,
               #   discovery, merge, Tier-3 LLM assist, Tier-4 interop)
tests/         # pytest suite
pyproject.toml # package metadata and installable dependencies
ROADMAP.md     # the living roadmap (source of truth; README links to it)
```
