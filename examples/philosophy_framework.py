#!/usr/bin/env python3
"""A philosophical framework built on valuez semantic + argument primitives.

Worked example: the classical analysis of *knowledge* and Gettier's challenge.

It shows how the platform models a philosophical framework as a traceable graph:

1. `Concept`s for the ideas (Knowledge, JustifiedTrueBelief, Truth, ...).
2. `Relation`s with a controlled *predicate vocabulary* and qualifiers
   (``modality`` like "necessary", ``strength`` in [0,1]) -- e.g.
   "JTB presupposes Justification [necessary]".
3. `Proposition`s (reified, truth-apt claims) and an `Argument` (premises =>
   conclusion) capturing Gettier's reductio, plus a rebutting argument.
4. `support` / `attack` relations between arguments (a Dung-style network).

Everything is ground-truthed via `Reference` (citations to the source texts),
persisted through `dotz`, and rendered as an interactive argument map.

Run:  python examples/philosophy_framework.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import (  # noqa: E402
    Argument,
    Concept,
    Proposition,
    Reference,
    Relation,
    Value,
    Vocabulary,
    visualize_arguments,
)
from valuez.repository import ValueRepository  # noqa: E402

# A controlled vocabulary of the relations our framework allows.
PREDICATES = Vocabulary(
    "philosophical_relations",
    ["defines", "presupposes", "entails", "contradicts", "supports", "attacks"],
    reference=Reference("Framework convention", description="Allowed relation types."),
)

PLATO = Reference("Plato, Theaetetus", locator="201c-210a")
GETTIER = Reference("Gettier (1963), 'Is Justified True Belief Knowledge?'")
CLARK = Reference("Clark (1963), 'Knowledge and Grounds' (no-false-lemmas response)")


def concepts() -> list[Concept]:
    return [
        Concept("Knowledge", definition="Cognitive success; the target of analysis.",
                id="c_knowledge", reference=PLATO),
        Concept("JustifiedTrueBelief", definition="Belief that is both true and justified.",
                id="c_jtb", reference=PLATO),
        Concept("Belief", id="c_belief"),
        Concept("Truth", id="c_truth"),
        Concept("Justification", id="c_justification"),
    ]


def concept_relations() -> list[Relation]:
    v = PREDICATES
    return [
        Relation("JustifiedTrueBelief", "defines", "Knowledge", vocabulary=v,
                 modality="proposed", strength=0.6, id="cr_def", reference=PLATO),
        Relation("JustifiedTrueBelief", "presupposes", "Belief", vocabulary=v,
                 modality="necessary", id="cr_belief"),
        Relation("JustifiedTrueBelief", "presupposes", "Truth", vocabulary=v,
                 modality="necessary", id="cr_truth"),
        Relation("JustifiedTrueBelief", "presupposes", "Justification", vocabulary=v,
                 modality="necessary", id="cr_just"),
    ]


def arguments_and_attacks():
    p1 = Proposition("Knowledge is justified true belief.", label="P1", id="p1",
                     reference=PLATO)
    p2 = Proposition("In Gettier cases a subject has a JTB that is not knowledge.",
                     truth_value=True, label="P2", id="p2", reference=GETTIER)
    c = Proposition("Justified true belief is not sufficient for knowledge.",
                    truth_value=True, label="C", id="pc", reference=GETTIER)
    p3 = Proposition("Knowledge requires justification resting on no false lemma.",
                     label="P3", id="p3", reference=CLARK)

    gettier = Argument([p1, p2], c, scheme="reductio", label="Gettier-Argument",
                       id="arg_gettier", reference=GETTIER)
    no_false_lemmas = Argument([p3], "The JTB analysis can be repaired.",
                               scheme="restriction", label="No-False-Lemmas",
                               id="arg_nfl", reference=CLARK)

    attacks = [
        Relation("Gettier-Argument", "attacks", "JustifiedTrueBelief",
                 vocabulary=PREDICATES, modality="defeasible", strength=0.9,
                 id="at_gettier", reference=GETTIER),
        Relation("No-False-Lemmas", "attacks", "Gettier-Argument",
                 vocabulary=PREDICATES, modality="defeasible", strength=0.5,
                 id="at_nfl", reference=CLARK),
    ]
    return [p1, p2, c, p3], [gettier, no_false_lemmas], attacks


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_philosophy"))
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = ValueRepository(data_dir=out_dir / "store")

    cs = concepts()
    crels = concept_relations()
    props, args, attacks = arguments_and_attacks()
    repo.add_values(cs + crels + props + args + attacks)

    line = "-" * 70
    print(line)
    print("valuez example: a philosophical framework (Gettier / analysis of knowledge)")
    print(line)
    print(f"Concepts   : {', '.join(c.name for c in cs)}")
    print()
    print("Concept relations (predicate [modality] (strength)):")
    for r in crels:
        print(f"  {r.source} --{r._edge_title()}--> {r.target}")
    print()
    print("Arguments:")
    for a in args:
        print(f"  {a.handle} [{a.scheme}]: {a.premises}  =>  {a.conclusion!r}")
    print()
    print("Argument-level moves (Dung-style):")
    for r in attacks:
        print(f"  {r.source} --{r._edge_title()}--> {r.target}   [{r.reference.source}]")
    print()

    # Persistence + query through dotz.
    kinds = sorted(set(repo.query("[].kind")))
    print(f"Persisted {len(repo.query('[]'))} values in dotz store {sorted(kinds)}")
    grounded = repo.query("[?reference] | length(@)")
    print(f"Ground-truthed (carry a Reference): {grounded} / {len(repo.query('[]'))}")

    # Rebuild typed objects from storage and render the argument map.
    stored_args = [Value.from_dict(d) for d in repo.query("[?kind=='argument']")]
    stored_attacks = [Value.from_dict(d) for d in repo.query("[?kind=='relation' && predicate=='attacks']")]
    graph_path = _render(stored_args, stored_attacks, out_dir)
    if graph_path:
        print(f"Argument map: {graph_path}")
    print(line)


def _render(args, attacks, out_dir: Path):
    try:
        import dotz.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)  # keep pyvis's vendored lib/ out of the working tree
        return visualize_arguments(args, "argument_map.html", relations=attacks).resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
