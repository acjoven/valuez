#!/usr/bin/env python3
"""Inference and tension detection: derived edges, clashes, gaps, Dung status.

``valuez.analyze`` generalizes the structural-order helpers in
``valuez.reasoning`` into one pass over a whole ontology. It *returns* derived
relations (never writes them into the canonical graph) and reports tensions
and gaps. Each derived edge carries a ``Reference`` naming the rule and the
asserted ids it rested on.

This demo runs three inventories:

1. A well-formed mereology (Cell ⊂ Tissue ⊂ Organ ⊂ Organism) -- transitivity.
2. The Gettier argument map -- Dung grounded status + open questions.
3. An illicit fragment (cycle + ``contrasts-with`` vs ``is-a``) -- tensions.
4. The committed Kant map -- how many is-a hops the closure adds, and whether
   the strict orders stay acyclic.

Run:  python examples/analysis_demo.py
"""
from __future__ import annotations

import json
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
    Universal,
    analyze,
)

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"
PLATO = Reference("Plato, Theaetetus")
GETTIER = Reference("Gettier (1963)")
CLARK = Reference("Clark (1963)")


def mereology():
    return [
        Universal("Cell", definition="Biological unit.", id="n_cell", reference=Reference("SEP, Mereology")),
        Universal("Tissue", definition="Cells together.", id="n_tissue", reference=Reference("SEP, Mereology")),
        Universal("Organ", definition="Tissues together.", id="n_organ", reference=Reference("SEP, Mereology")),
        Universal("Organism", definition="A living whole.", id="n_org", reference=Reference("SEP, Mereology")),
        Relation("Cell", "part-of", "Tissue", id="e1"),
        Relation("Tissue", "part-of", "Organ", id="e2"),
        Relation("Organ", "part-of", "Organism", id="e3"),
    ]


def gettier():
    p1 = Proposition("Knowledge is justified true belief.", label="P1", id="p1", reference=PLATO)
    p2 = Proposition("In Gettier cases a subject has a JTB that is not knowledge.",
                     truth_value=True, label="P2", id="p2", reference=GETTIER)
    c = Proposition("Justified true belief is not sufficient for knowledge.",
                    truth_value=True, label="C", id="pc", reference=GETTIER)
    p3 = Proposition("Knowledge requires justification resting on no false lemma.",
                     label="P3", id="p3", reference=CLARK)
    return [
        Concept("JustifiedTrueBelief", definition="Belief that is true and justified.",
                id="c_jtb", reference=PLATO),
        p1, p2, c, p3,
        Argument([p1, p2], c, scheme="reductio", label="Gettier-Argument",
                 id="arg_g", reference=GETTIER),
        Argument([p3], "The JTB analysis can be repaired.", scheme="restriction",
                 label="No-False-Lemmas", id="arg_n", reference=CLARK),
        Relation("Gettier-Argument", "attacks", "JustifiedTrueBelief", id="atk_jtb",
                 reference=GETTIER),
        Relation("No-False-Lemmas", "attacks", "Gettier-Argument", id="atk_g",
                 reference=CLARK),
    ]


def illicit():
    return [
        Universal("Freedom", definition="spontaneity", id="n_f"),
        Universal("Nature", definition="mechanism", id="n_n"),
        Universal("Cause", definition="ground of change", id="n_c"),
        Relation("Freedom", "contrasts-with", "Nature", id="cx"),
        Relation("Freedom", "is-a", "Cause", id="isa1"),
        Relation("Cause", "is-a", "Nature", id="isa2"),
        Relation("Nature", "grounds", "Cause", id="g1"),
        Relation("Cause", "grounds", "Nature", id="g2"),
    ]


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_analysis"))
    out_dir.mkdir(parents=True, exist_ok=True)

    line = "-" * 72
    print(line)
    print("valuez analysis: inference + tension detection")
    print(line)

    print("1. Mereology -- transitivity of part-of")
    mere = analyze(mereology(), dung=False)
    print(mere.summary())
    for d in mere.derived:
        print(f"    {d.relation.source} -{d.relation.predicate}[inferred]-> "
              f"{d.relation.target}  because {list(d.because)}")
    print()

    print("2. Gettier -- Dung grounded status and open questions")
    g = analyze(gettier())
    print(g.summary())
    print()

    print("3. Illicit fragment -- cycle + contrasts-with vs is-a")
    bad = analyze(illicit(), dung=False)
    print(bad.summary())
    print()

    print("4. Kant ontology")
    docs = json.loads((ONTOLOGIES / "kant.json").read_text(encoding="utf-8"))
    kant = analyze(docs, dung=False)
    print(kant.summary())
    isa = [d for d in kant.derived if d.relation.predicate == "is-a"]
    print(f"    is-a closure adds {len(isa)} inferred edge(s); "
          f"e.g. {isa[0].relation.source} is-a {isa[0].relation.target}" if isa else "")

    (out_dir / "analysis_kant.json").write_text(
        json.dumps(kant.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Kant analysis written: {out_dir / 'analysis_kant.json'}")
    print(line)


if __name__ == "__main__":
    main()
