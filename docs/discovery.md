# Cross-universe discovery

`valuez.discovery` is the first slice of roadmap item 5: given a merged
universe, find **unexpected connections** — shortest paths from a concept
that lived in only one source to a concept that lived only in another,
passing through a join point the merge created.

Thematic clustering and proposing *new* bridging concepts are later slices.
This module does not write anything into the canonical graph.

## Why

`merge_ontologies` stitches two maps at shared names. The merge report lists
those join points. It does not tell you what became *newly close*.

Take the two small gas maps under `ontologies/` (see [`merge.md`](merge.md)):
`thermodynamics.json` describes a gas without mentioning molecules, and
`kinetic_theory.json` starts from them. They share `Temperature`.

- The thermodynamics map's `ReversibleEngine` never mentions the kinetic-theory
  map's `MeanKineticEnergy`.
- After the join, both attach to `Temperature`.
- The 2-hop walk `ReversibleEngine -defines-> Temperature -measures-> MeanKineticEnergy`
  exists only in the merged universe.

That walk is a *crossing*. Crossings are the connections neither map drew.

## What counts as a crossing

A node is **exclusive** to a source when `MergeReport.node_sources[name]`
has length 1, and a **join point** when it has length ≥ 2. Keys are the
alias-resolved names, so a curated alias (`aliases=[["IdealGas", "PerfectGas"]]`)
creates a new join point and new crossings through it. This is almost always
the same set as `report.join_points`; the exception is an alias that folds two
names from the *same* source, which `join_points` lists but discovery treats as
still exclusive to that source.

A crossing is a shortest path from an exclusive node of source A to an
exclusive node of source B such that:

- the walk is **undirected** by default (same as `Graph.how`)
- it is at most `cutoff` hops (default 3)
- it has **at least two hops** (a 1-hop exclusive–exclusive edge is not a
  merge artifact — it is a dangling endpoint that the other source happened
  to satisfy). If that 1-hop edge is the *shortest* path, the longer route
  through a join is not reported either: a crossing is the shortest path,
  not every path that happens to visit a join.
- at least one **interior** node is a join point (`via`)

Both directions are collected (A→B and B→A) so
`between("thermodynamics", "kinetic_theory")` and the reverse both work.
Isolated exclusive nodes never start a crossing.

## API

```python
from valuez import discover, merge_ontologies

res = merge_ontologies(["ontologies/thermodynamics.json", "ontologies/kinetic_theory.json"])
found = res.discover(cutoff=2)             # or discover(res, ...)
print(found.summary())                     # 12 crossings: 6 in each direction

found.between("thermodynamics", "kinetic_theory")   # one direction (6)
found.via("Temperature")                   # crossings that pass through Temperature (4)
found.hubs                                 # join points ranked by crossing count
found.exclusive["thermodynamics"]          # names that lived only in that map
```

`discover()` also accepts anything `merge_ontologies` accepts (file paths,
repos, value iterables), so you can skip the explicit merge:

```python
found = discover(["ontologies/thermodynamics.json", "ontologies/kinetic_theory.json"])
```

| Parameter | Default | Meaning |
| --- | --- | --- |
| `cutoff` | `3` | Max hops on each shortest path. |
| `limit` | `40` | Ranked window to keep (`0` = all). Ranking is hops, then start, end, sources. |
| `directed` | `False` | Follow asserted arrows only when `True`. |

`Discovery.total` is the count **before** `limit`. `hubs` is counted on that
full set, so truncating the ranked list does not hide which join points carry
the traffic.

Each `Crossing` holds the `Path` (asserted edges, so provenance rides along),
`from_source` / `to_source`, and `via` (join points on the interior).
`describe()` renders:

```
ReversibleEngine [thermodynamics] ~ Temperature ~ MeanKineticEnergy [kinetic_theory]  (2 hop(s))
  ReversibleEngine -defines-> Temperature -measures-> MeanKineticEnergy
```

`MergeReport.node_sources` is filled by every merge (exclusive names as well
as join points). Older `MergeResult` objects built before this field existed
raise from `discover()` so you re-merge.

## What this slice does *not* do

- Thematic clustering of exclusive neighborhoods.
- Proposing **new** bridging concepts (a later synthesis step).
- Automatic alignment of near-synonyms. Curated `aliases` on
  `merge_ontologies` already feed discovery; meaning-based candidate alignment
  is the next slice of merge alignment, item 1.
- Writing crossings into the canonical ontology. They are a report, like
  derived analysis edges: reviewable, not auto-committed.
- Depending on `analyze()` / concept briefs. Path-based discovery needs
  merge + `Graph`; analysis can annotate a crossing later.

## Example

`examples/merge_demo.py` builds the two small gas maps, merges them, and lists
the six crossings from the thermodynamics map into the kinetic-theory map.

`examples/discovery_demo.py` does the same at scale: it merges the committed
Kant and Kierkegaard maps, prints the ranked crossings at `cutoff=2` (`limit=0`
keeps all), and writes `crossings.json` plus an HTML subgraph of the shortest
ones.
