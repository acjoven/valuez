# Inference and tension detection

`valuez.analyze` is the first slice of roadmap item 4. It generalizes
[`valuez.reasoning`](../valuez/reasoning.py) -- transitive closure and cycle
checks of *one* predicate -- into a single pass over a whole ontology that
**infers**, **flags tensions**, **lists gaps**, and scores arguments.

Derived items are *returned*, never written into the canonical graph. Each
carries a `Reference` (`source="valuez.analysis"`) whose `metadata["rule"]` and
`metadata["because"]` name the rule and the asserted edge ids it rested on, so
a derived edge is as auditable as an asserted one. Meaning-bearing content still
enters the map only through a human-reviewed path.

## What it does

| Bucket | What | Notes |
| --- | --- | --- |
| **Derived** | new `Relation`s / `Instantiation`s | `modality="inferred"`; deterministic ids `inferred:<rule>:...` |
| **Tensions** | cycles, predicate clashes, contradictory truth-values | illicit *structure*, not a judgment of the content |
| **Gaps** | dangling / isolated / undefined / ungrounded nodes; open questions; missing premises | inventory of unfinished work |
| **Arguments** | Dung *grounded* status | `accepted` / `defeated` / `undecided` under `attacks` |

### Inference rules (this slice)

1. **transitivity** of `is-a`, `part-of`, `grounds`, `presupposes`, `requires`
   (override with `transitive=...`). The supporting path's asserted ids are
   `because`.
2. **symmetry** of `contrasts-with` and `contradicts` (override with
   `symmetric=...`).
3. **instantiation-inheritance** -- if `I instantiates U` and `U is-a V`
   (asserted or by closure), emit `I instantiates V`. Disable with
   `inherit_instantiation=False`.

Rules do not re-emit an asserted `(source, predicate, target)`.

### Tensions

- **cycle** -- a loop in a strict-order predicate.
- **clash** -- the same two nodes related by both a contrast/contradiction (or
  `attacks`/`supports`) *and* a subsumption-like predicate (`is-a`,
  `instantiates`, `part-of`, `grounds`). Derived `is-a` counts, so a contrast
  with an ancestor is a clash.
- **contradiction** -- two `Proposition`s share a statement (or handle) with
  `truth_value` True and False.

### Gaps

Reported only when the input includes concept documents (relations-only input
does not flag every endpoint as dangling):

- `dangling` -- an edge endpoint is not a declared node
- `isolated` -- a declared node with no incident edge
- `undefined` -- a node with no `definition`
- `ungrounded` -- a node with no `Reference` *and* no incident asserted edge
  that carries one (citation on an edge counts)
- `open-question` -- a `Proposition` whose `truth_value` is `None`
- `missing-premise` -- an `Argument` names a handle that is not a proposition

### Dung grounded semantics

Argument handles are nodes; `attacks` edges whose *both* ends are arguments
are the attack relation. (An argument attacking a *concept* is ignored for
scoring; it is still an ordinary edge.) Grounded extension:

- an argument is **accepted** iff every attacker is defeated;
- **defeated** iff some accepted argument attacks it;
- otherwise **undecided** (e.g. a mutual attack).

Bipolar `supports`, preferred/stable extensions, and graded strength are later
slices.

## API

```python
from valuez import analyze

report = analyze(values)                 # Value objects or document dicts
report = book.analyze()                  # Reading
report = repo.analyze()                  # ValueRepository
report = merge_result.analyze()

report.derived                           # [Derivation(rule, relation, because), ...]
report.relations                         # the derived Relation objects
report.tensions, report.gaps             # [Finding(kind, detail, items), ...]
report.arguments                         # {"Gettier-Argument": "defeated", ...}
print(report.summary())
report.to_dict()
```

Flags: `transitive=`, `symmetric=`, `inherit_instantiation=`, `tensions=`,
`gaps=`, `dung=`.

The low-level helpers `reasoning.infer_transitive` / `is_acyclic` /
`find_cycles` stay as they are and are what the rules call.

## Example

`examples/analysis_demo.py` runs three small fragments built to have something
to find: a mereology (transitivity), the Gettier map (Dung + open questions),
and an illicit cycle+clash. It then runs one of the large maps
(`ontologies/kant.json`) to show the closure at scale.

The two small gas maps under `ontologies/` come back clean, alone and merged
(`Analysis: 0 derived, 0 tension(s), 0 gap(s)`): they have no chains for the
transitive rules to extend and no arguments to score.

## Not in this slice

- User-authored rule language / arbitrary Horn clauses.
- Derived *propositions* (only relations for now).
- Preferred/stable/complete Dung semantics; `supports` as a bipolar attack-defence.
- Writing derived edges into a `Reading` or a store (that remains a review step).
- Using `strength` as a weight.
