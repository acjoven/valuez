# Merging ontologies into one universe

`valuez.merge_ontologies` folds several independently-authored ontologies into a
single connected graph by **identifying points of overlap and joining the common
nodes**. It is the counterpart to `ValueRepository.export_ontology`: export makes
one map reviewable; merge makes many maps *one universe*.

## Why join on name

Every edge in a `valuez` graph -- a `Relation` or an `Instantiation` -- stores
its endpoints **by name**, not by id (`valuez/semantic.py`). So the identity that
matters across files is a node's `name`. When two ontologies each define a node
called `Freedom`, joining them is simply: collapse the two `Freedom` documents
into one. Every edge that referenced `"Freedom"` in either file now points at the
single surviving node, and the two subgraphs become connected *through* it -- no
edge rewriting required.

This is exactly why `examples/kant_ontology.py` and
`examples/kierkegaard_ontology.py` were built to the same shape and deliberately
share names (the Kierkegaard map's `MERGE_ANCHORS`): they are the fixtures that
make a merge meaningful.

## What gets merged

| Document kind | Identity | Merge behavior |
| --- | --- | --- |
| `concept` / `individual` / `universal` | `name` | **Joined.** Same-named nodes collapse into one; a name in >1 source is a *join point*. |
| `relation` / `instantiation` | `(source, predicate, target, modality, strength)` | Carried over; identical triples de-duplicated (shared provenance reported). |
| everything else (`proposition`, `argument`, `scalar`, ...) | `id` | Carried over as-is; a final pass guarantees globally unique ids. |

## Reconciling a join point

When contributors to one name disagree, `on_conflict` decides:

- `"first"` (default) — keep the first source's value for a conflicting field;
  missing fields are filled in from later sources.
- `"last"` — keep the last source's value.
- `"raise"` — refuse to merge (raises `ValueError`).

Two flavors of divergence are recorded on the `MergeReport` either way:

- **field conflict** — the same node has a different `definition`,
  `ontological_status`, `label`, or `reference` in each source (e.g. `Existence`
  is an *a priori category of modality* for Kant but an *existential task* for
  Kierkegaard). Under `first`/`last` these resolve silently but are reported.
- **type conflict** — the same name is an `individual` in one source and a
  `universal` in another. Always reported; `raise` refuses it.

## Result and report

`merge_ontologies(...)` returns a `MergeResult`:

- `.documents` — the merged document dicts (sorted by id).
- `.values()` / `.relations()` / `.named_nodes()` — rehydrated `Value` objects.
- `.to_repository(data_dir=...)` — persist into a `ValueRepository`.
- `.export(path)` — write one canonical, deterministic universe JSON.
- `.report` — a `MergeReport` with `join_points`, `node_sources` (every named
  node → contributing source labels; length 1 = exclusive, ≥2 = join),
  `field_conflicts`, `type_conflicts`, edge de-duplication counts,
  `id_collisions`, `dangling_edges`, and a `summary()` / `to_dict()`.
- `.graph()` — relation graph over the merged universe.
- `.discover(...)` — exclusive-to-exclusive paths that exist only because
  the maps were joined; see [`discovery.md`](discovery.md).

```python
from valuez import merge_ontologies

res = merge_ontologies(["ontologies/kant.json", "ontologies/kierkegaard.json"])
print(res.report.summary())
res.export("ontologies/universe.json")     # optional: a derived, regenerable map
```

Sources may be file paths, `ValueRepository` instances, or iterables of `Value`
objects / document dicts, so you can merge committed files, in-memory `Reading`
sessions, or a mix.

See `examples/merge_universe.py` for a worked run that merges Kant + Kierkegaard,
shows how each join point stitches the two graphs together, and renders a legible
"seam" of just the edges incident to the shared nodes.

## Referential integrity

The merged universe is checked: any edge whose endpoint is not a node in the
union is reported as a `dangling_edge` (a warning, not a hard failure, so partial
maps still merge). Merging the two committed ontologies yields zero dangling
edges.

## Scope and future work

- **Name is the only key.** There is no fuzzy matching or synonym resolution:
  `TheSelf` (Kierkegaard) and `Soul` (Kant) are near-synonyms but merge only if a
  future alias/`sameAs` layer maps them. That belongs with the Tier-4
  interoperability work (`owl:sameAs` / SKOS `exactMatch`); see
  [`interoperability.md`](interoperability.md).
- **Provenance** currently lives in the `MergeReport`, not stamped onto each
  merged document (so the exported universe stays cleanly round-trippable). A
  future option could annotate each node/edge with its contributing sources.
- **N-way merges** work today (pass more than two sources); conflict reporting is
  pairwise-agnostic (it lists every contributor per name).
