# Graph traversal and path queries

`valuez.traversal` is the first slice of the *active knowledge* track: a
query API over the relation graph you already have. Capture and structure
(authoring, persistence, merge) stay as they are; this layer lets you **walk**
the result.

It is *mechanics*. Traversal never invents nodes or edges. Every hop on a
returned path is an asserted `Relation` / `Instantiation`, so provenance
rides along.

## Why

Until this slice, the only ways to inspect a stored map were exact-name join
(`merge_ontologies`) and JMESPath over flat documents (`ValueRepository.query`).
Neither answers:

- what sits next to `Pressure`?
- how does `MolecularCollision` relate to `Temperature`?
- what is the topic around `InternalEnergy`?

Those questions are the foundation for concept briefs, path-based
cross-universe discovery, and guided reading (see [`ROADMAP.md`](../ROADMAP.md)).

## API

The unit of work is a `Graph`, keyed by concept **name** (the same identity
edges already use):

```python
from valuez import Graph, Reading

g = book.graph()                          # a Reading / OntologyBuilder
g = repo.graph()                          # a ValueRepository
g = merge_result.graph()                  # a merged universe
g = Graph.from_ontology("ontologies/kinetic_theory.json")   # a committed map

g.neighbors("Pressure")                   # adjacent names
g.neighborhood("Pressure", hops=2)        # k-hop vicinity + induced edges
g.how("MolecularCollision", "Temperature")   # shortest connecting path (undirected)
g.shortest_path("IdealGas", "Molecule")   # directed by default
g.shortest_paths_from("Pressure")         # one BFS: shortest path to every reachable node
g.paths("Pressure", "MeanKineticEnergy", cutoff=4, limit=10)   # simple paths, shortest first
g.topic("Pressure", hops=1)               # induced subgraph around one or more seeds
g.topic(["Pressure", "InternalEnergy"], hops=1)
g.incident("Pressure", predicates="depends-on")
g.visualize("pressure.html")
```

The names are from `ontologies/kinetic_theory.json`, a nine-concept map of a
gas as molecules in motion (built by `examples/merge_demo.py`). On it:

```
>>> g.neighbors("Pressure")
['MeanKineticEnergy', 'MolecularCollision', 'Temperature', 'Volume']
>>> print(g.how("MolecularCollision", "Temperature"))
MolecularCollision -causes-> Pressure -depends-on-> Temperature
>>> print(g.shortest_path("IdealGas", "Molecule"))
IdealGas -is-a-> Gas -made-of-> Molecule
>>> for path in g.paths("Pressure", "MeanKineticEnergy", cutoff=4, limit=10):
...     print(path)
Pressure -depends-on-> MeanKineticEnergy
Pressure -depends-on-> Temperature -measures-> MeanKineticEnergy
```

Functional aliases matching `valuez.reasoning` also exist (`how(relations, a, b)`,
`neighborhood(...)`, `paths(...)`, `topic(...)`) for callers that already have
a list of edges.

### Direction

| Method | Default | Meaning |
| --- | --- | --- |
| `neighbors` / `neighborhood` / `topic` / `incident` | `direction="both"` | Walk the underlying undirected graph. `"out"` / `"in"` restrict discovery. |
| `how` / `paths` | `directed=False` | "How are these related?" does not require knowing the arrow. |
| `shortest_path` | `directed=True` | Follow asserted edge direction; the reverse walk is `None`. |

When an undirected walk runs *against* an asserted edge, `Path.describe()`
renders a reverse arrow:

```
>>> print(g.how("Temperature", "MolecularCollision"))
Temperature <-depends-on- Pressure <-causes- MolecularCollision
```

### Predicate filters

Any query accepts `predicates="is-a"` or `predicates=["is-a", "part-of"]`.
This is the hook later learning workflows will use for topological reading
order over `presupposes` / `requires` / `grounds`.

### Isolated nodes

`Graph.from_values` / `from_ontology` keep named `Concept` / `Individual` /
`Universal` nodes even when they have no incident edge. Building from a bare
list of relations only sees endpoints.

### Paths

A `Path` is nodes interleaved with `Hop`s. Each hop holds the asserted
`Relation`(s) that connect that pair (parallel predicates are joined with
`|` in `describe()`). `path.relations` is the flattened list — the citations
on those edges are the provenance of the walk.

Unknown names raise `ValueError` (eager, like `Reading.relate`). Disconnected
nodes return `None` from `how` / `shortest_path` and `[]` from `paths`.

## What this slice does *not* do

Left for later items on the same track:

- Concept briefs / `explain(node)` (needs this graph, plus bibliography).
- Typed forward-chaining inference and tension detection (`reasoning.py`
  stays the structural-order helper it is).
- Weighted paths (e.g. by `strength`), argument-map traversal, clustering.

Path-based cross-universe discovery now lives in [`discovery.md`](discovery.md).

## Example

`examples/traversal_demo.py` asks these questions of a small reading session,
then repeats them at scale on one of the large maps (`ontologies/kant.json`)
and writes a topic-subgraph HTML.
