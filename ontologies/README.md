# Ontologies

Canonical, **committed** ontology maps — the source of truth for hand-authored
`valuez` data.

Each file here is a single JSON array of serialized `Value` documents (concepts,
relations, individuals/universals, scalars, ...), produced by
`ValueRepository.export_ontology(...)`. Keeping one sorted, stable-key file per
ontology (instead of the expanded per-document `dots` store) makes changes small
and reviewable in git.

## Workflow

Author / update a map, then export the canonical file:

```python
from valuez.repository import ValueRepository

repo = ValueRepository(data_dir="/tmp/my_store")  # local, gitignored cache
repo.add_values([...])                             # build with valuez primitives
repo.export_ontology("ontologies/my_map.json")     # commit this file
```

Read / query / visualize a committed map (rehydrates into a throwaway store):

```python
repo = ValueRepository.from_ontology("ontologies/my_map.json",
                                     data_dir="/tmp/my_store")
repo.query("[?kind=='relation']")
```

## Conventions

- **Use deterministic, human-readable ids** (e.g. `u_human`, `isa_hm`) when
  constructing values. The `dots` store defaults to random UUID filenames, which
  churn on every rebuild; stable ids keep diffs meaningful.
- **Commit the `ontologies/*.json` files here.** The expanded per-document store,
  generated graph `*.html`, and pyvis `lib/` are regenerable and are gitignored.
- **To delete/rename**, rebuild the canonical file (load into a fresh `data_dir`)
  rather than layering ingests, since `ingest` never removes stale documents.
