# Concept briefs — `explain(node)`

`valuez.explain` assembles a readable page for one node of an ontology. It is
the second slice of the *active knowledge* track: traversal
([`docs/traversal.md`](traversal.md)) lets you walk a map; a brief lets you
**read** one node of it.

## What a brief contains

| Section | Source | Notes |
| --- | --- | --- |
| Header | the `Concept` / `Individual` / `Universal` doc | kind, `ontological_status`, definition, the node's own citation |
| Relations | every `Relation` / `Instantiation` touching the name | outgoing then incoming, sorted by predicate; modality / strength and the edge's citation inline |
| Claims | `Proposition`s that bear on the node | see *linking* below |
| Arguments | `Argument`s that bear on the node | premises and conclusion listed |
| Mentioned in definitions of | other concepts whose `definition` names this node | textual, always labelled |
| Sources | distinct `Reference`s behind everything above | grouped by `source`, locators listed |

## Linking claims and arguments

Edges reference concepts by **name**; propositions and arguments are keyed by
**handle** (`label` or statement). The two vocabularies only meet when a
relation's endpoint is a handle (`Gettier-Argument --attacks--> JustifiedTrueBelief`).
That is the structural link, marked `edge`.

In the committed maps, claims and arguments are cited but not wired to concepts
by edge, so a brief also looks for **mentions**: a whole-word, case-insensitive
match of the concept name (and its de-CamelCased form, so `InternalEnergy`
matches "the internal energy") in a proposition's statement or an argument's
premises / conclusion. In the kinetic-theory map, the claim "The mean molecular
kinetic energy is a property only of the temperature." attaches to
`Temperature` this way. Hits are marked `mention` in `to_dict()` and rendered
as `(…; mention)` in Markdown, so a reader never confuses a textual hit with an
asserted relation. Pass `mentions=False` to keep only edge-linked items.

This is the one heuristic in the module. It adds no content; it surfaces
existing, cited content that names the node.

## API

```python
from valuez import explain

brief = explain(values, "Temperature")      # values: Value objects or document dicts
brief = book.explain("Temperature")         # Reading
brief = repo.explain("Temperature")         # ValueRepository
brief = merge_result.explain("Temperature") # merged universe

brief.definition, brief.kind, brief.ontological_status
brief.outgoing, brief.incoming, brief.neighbors
brief.by_predicate("in")                    # {"defines": ["ReversibleEngine"], "depends-on": ["Entropy", ...]}
brief.propositions                          # [(Proposition, "edge" | "mention"), ...]
brief.arguments                             # [(Argument, "edge" | "mention"), ...]
brief.citations()                           # distinct References, node first
brief.sources()                             # {"Feynman, Leighton & Sands, ...": ["39-4", "39-5", "44-2", ...]}
brief.bibliography()                        # ReferenceRepository (passage-only refs included)
brief.to_markdown(); brief.to_dict()
```

`explain` raises `ValueError` for a name that is neither a declared node nor an
edge endpoint. A name that appears only on edges (a dangling endpoint) still
gets a brief, with `node=None`.

`Brief.values()` returns everything the brief drew on, so a brief doubles as a
cited *slice* of the ontology you can hand to `ReferenceRepository.from_values`
or persist.

## On a merged universe

Because merge joins nodes by name, a brief on a merged universe is one page
whose relations and sources come from every contributing map.

Take `Temperature` in the two small gas maps (see [`merge.md`](merge.md)). In
`kinetic_theory.json` alone it has two relations, both cited to chapter 39.
After the merge it has five, and the page cites sections of both chapters:

```python
from valuez import merge_ontologies

universe = merge_ontologies(["ontologies/thermodynamics.json", "ontologies/kinetic_theory.json"])
print(universe.explain("Temperature").to_markdown())
```

```
# Temperature
*concept*
Cited: Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 44-5

How hot an object is, set by the heat a reversible engine absorbs from it.

## Relations
- Temperature —measures→ MeanKineticEnergy  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 39-4)
- ReversibleEngine —defines→ Temperature  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 44-5)
- Entropy —depends-on→ Temperature  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 44-6)
- InternalEnergy —depends-on→ Temperature  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 44-6)
- Pressure —depends-on→ Temperature  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 44-6)

## Claims
- **P-MeanEnergy** — The mean molecular kinetic energy is a property only of the temperature. (asserted)  (Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963), 39-4; mention)

## Mentioned in definitions of
- Entropy, HeatEngine, IdealGas, Pressure, SecondLaw

## Sources
- Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963) — 39-4, 39-5, 44-2, 44-3, 44-5, 44-6
```

The definition shown is the thermodynamics one, because that map came first
and the default conflict policy keeps the first source's fields. The merge
report still lists both definitions.

`examples/concept_brief.py` does the same at scale: it briefs `Freedom` in one
of the large maps, then in the merged pair, where the page draws on both maps'
edges and sources.

## Not in this slice

- Inferred relations (transitive `is-a` ancestry) — `reasoning.py` can supply
  them; a brief shows asserted edges only.
- Rendering to HTML / a UI, and cross-linking briefs.
- Ranking or summarising: a brief lists, it does not judge.
