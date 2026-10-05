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

In the curated maps, arguments are cited but not wired to concepts by edge, so a
brief also looks for **mentions**: a whole-word, case-insensitive match of the
concept name (and its de-CamelCased form, so `MoralLaw` matches "the moral law")
in a proposition's statement or an argument's premises / conclusion. Hits are
marked `mention` in `to_dict()` and rendered as `(…; mention)` in Markdown, so a
reader never confuses a textual hit with an asserted relation. Pass
`mentions=False` to keep only edge-linked items.

This is the one heuristic in the module. It adds no content; it surfaces
existing, cited content that names the node.

## API

```python
from valuez import explain

brief = explain(values, "Freedom")          # values: Value objects or document dicts
brief = book.explain("Freedom")             # Reading
brief = repo.explain("Freedom")             # ValueRepository
brief = merge_result.explain("Freedom")     # merged universe

brief.definition, brief.kind, brief.ontological_status
brief.outgoing, brief.incoming, brief.neighbors
brief.by_predicate("out")                   # {"is-a": ["MoralConcept", "Postulate"], ...}
brief.propositions                          # [(Proposition, "edge" | "mention"), ...]
brief.arguments                             # [(Argument, "edge" | "mention"), ...]
brief.citations()                           # distinct References, node first
brief.sources()                             # {"Kant, CPrR (1788)": ["5:29", ...], ...}
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

Because merge joins nodes by name, `MergeResult.explain("Freedom")` produces one
page whose relations and sources come from every contributing map — the Kant
edges and the Kierkegaard edges, with both authors under **Sources**. See
`examples/concept_brief.py`.

## Not in this slice

- Inferred relations (transitive `is-a` ancestry) — `reasoning.py` can supply
  them; a brief shows asserted edges only.
- Rendering to HTML / a UI, and cross-linking briefs.
- Ranking or summarising: a brief lists, it does not judge.
