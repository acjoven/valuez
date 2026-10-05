# Cross-universe discovery

`valuez.discovery` is the first slice of roadmap item 5: given a merged
universe, find **unexpected connections** — shortest paths from a concept
that lived in only one source to a concept that lived only in another,
passing through a join point the merge created.

Thematic clustering and proposing *new* bridging concepts are later slices.
This module does not write anything into the canonical graph.

## Why

`merge_ontologies` stitches two maps at shared names (`Freedom`, `God`,
...). The merge report lists those join points. It does not tell you what
became *newly close*:

- Kant's `TranscendentalIdealism` never mentioned Kierkegaard's `Anxiety`.
- After the join, both attach to `Freedom`.
- The 2-hop walk `TranscendentalIdealism -grounds-> Freedom -produces-> Anxiety`
  exists only in the merged universe.

That walk is a *crossing*. Crossings are the connections neither author drew.

## What counts as a crossing

A node is **exclusive** to a source when `MergeReport.node_sources[name]`
has length 1, and a **join point** when it has length ≥ 2. Keys are the
alias-resolved names, so a curated alias (`aliases=[["TheSelf", "Soul"]]`)
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

Both directions are collected (A→B and B→A) so `between("kant", "kierkegaard")`
and the reverse both work. Isolated exclusive nodes never start a crossing.

## API

```python
from valuez import discover, merge_ontologies

res = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"])
found = res.discover(cutoff=2, limit=24)   # or discover(res, ...)
print(found.summary())

found.between("kant", "kierkegaard")       # one direction
found.via("Freedom")                       # crossings that pass through Freedom
found.hubs                                 # join points ranked by crossing count
found.exclusive["kant"]                    # names that lived only in Kant
```

`discover()` also accepts anything `merge_ontologies` accepts (file paths,
repos, value iterables), so you can skip the explicit merge:

```python
found = discover(["ontologies/kant.json", "ontologies/kierkegaard.json"])
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
TranscendentalIdealism [kant] ~ Freedom ~ Anxiety [kierkegaard]  (2 hop(s))
  TranscendentalIdealism -grounds-> Freedom -produces-> Anxiety
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

`examples/discovery_demo.py` merges the committed Kant and Kierkegaard maps,
prints the ranked crossings at `cutoff=2` (`limit=0` keeps all), and writes
`crossings.json` plus an HTML subgraph of the shortest ones.
