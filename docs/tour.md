# A tour of valuez

The longer walk through the library: the value types, then persistence,
merging, traversal, briefs, analysis, discovery, and source management. For the
short version, see the [README](../README.md); for a first runnable script, see
[`examples/quickstart.py`](../examples/quickstart.py).

Paths in the snippets are relative to the repo root. The merge, traversal,
brief, and discovery snippets load the two large maps under
[`ontologies/`](../ontologies/README.md); see
[Worked corpora](../README.md#worked-corpora-two-large-maps) for what those are
and are not.

---

## The value system

Every type below subclasses [`Value`](../valuez/values.py): it has a stable `id`, an
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

[`ValueRepository`](../valuez/repository.py) is an OOP cover over the functional
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
[`ontologies/README.md`](../ontologies/README.md)).

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

See [`merge.md`](merge.md) and `examples/merge_universe.py`.

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
the same object. See [`traversal.md`](traversal.md).

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
a store. See [`briefs.md`](briefs.md).

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

See [`analysis.md`](analysis.md).

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

See [`discovery.md`](discovery.md) and `examples/discovery_demo.py`.

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

