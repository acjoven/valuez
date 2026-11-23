# Ontologies

Canonical, **committed** ontology maps — the source of truth for hand-authored
`valuez` data.

Each file here is a single JSON array of serialized `Value` documents (concepts,
relations, individuals/universals, scalars, ...), produced by
`ValueRepository.export_ontology(...)`. Keeping one sorted, stable-key file per
ontology (instead of the expanded per-document `dotz` store) makes changes small
and reviewable in git.

## Available maps

| File | Builder | What it maps |
| --- | --- | --- |
| `thermodynamics.json` | `examples/merge_demo.py` | A gas described without molecules: heat, work, engines, entropy. 12 concepts from chapter 44 of the Feynman Lectures, Vol. I (ids `td_*`). |
| `kinetic_theory.json` | `examples/merge_demo.py` | The same gas as molecules in motion. 9 concepts from chapter 39 (ids `kt_*`). |
| `kant.json` | `examples/kant_ontology.py` | Kant's critical philosophy across the three Critiques (ids `k_*`). |
| `kierkegaard.json` | `examples/kierkegaard_ontology.py` | Kierkegaard's existential authorship (ids `kk_*`). |

The maps come in two pairs, one small and one large. Each pair is two
**independent** graphs that overlap by *name* while their ids are disjoint, so
they are the fixtures for the **merge** function (`valuez.merge_ontologies`),
which folds multiple exported files into one universe by keying on name and
resolving collisions.

- `thermodynamics.json` and `kinetic_theory.json` share four names. `Volume`
  means the same in both; `Temperature`, `Pressure`, and `InternalEnergy` are
  defined differently by each. Start here: the whole merge fits on one screen
  (`examples/merge_demo.py`).
- `kant.json` and `kierkegaard.json` share nine, among them `Philosopher` and
  `PhilosophicalWork` (same meaning) and `Existence` / `Freedom` / `God` /
  `Reason` (different meanings). This is the same merge at a few hundred nodes
  each (`examples/merge_universe.py`).

See [`../docs/merge.md`](../docs/merge.md). A merged universe is *derived*
(regenerable from its sources), so it is intentionally **not** committed here.

The two large maps are test material, not a canon. Including an author is not
an endorsement of their views, and leaving one out is not a judgment. Each map
describes what its cited texts say, not what `valuez` holds to be true. Maps of
other traditions and fields are welcome.

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
  constructing values. The `dotz` store defaults to random UUID filenames, which
  churn on every rebuild; stable ids keep diffs meaningful.
- **Commit the `ontologies/*.json` files here.** The expanded per-document store,
  generated graph `*.html`, and pyvis `lib/` are regenerable and are gitignored.
- **To delete/rename**, rebuild the canonical file (load into a fresh `data_dir`)
  rather than layering ingests, since `ingest` never removes stale documents.
