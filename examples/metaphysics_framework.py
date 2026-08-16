#!/usr/bin/env python3
"""A metaphysical framework built on valuez' particular/universal primitives.

Worked example: a small ontology of *particulars* and *universals* and the
relations that structure them.

It shows how the platform models a metaphysics as a traceable graph:

1. `Universal`s (kinds/properties: LivingThing, Animal, Mammal, Human, colours)
   and `Individual`s (particulars: Socrates, Plato, this-apple), each carrying an
   optional `ontological_status` ("concrete" / "abstract" / "fundamental").
2. `Instantiation` edges -- a *typed* relation forcing Individual --instantiates--> Universal.
3. `Relation`s over a controlled predicate vocabulary for the structural orders:
   `is-a` (kind subsumption), `part-of` (mereology), `grounds` (determinate =>
   determinable).
4. The `reasoning` helper: transitive closure of `is-a` / `part-of` (deriving new
   *inferred* edges) and an acyclicity check on `grounds` (a strict order must
   have no cycles) -- with a deliberately broken mini-ontology to show cycle
   detection at work.

Everything is ground-truthed via `Reference`, persisted through `dotz`, and
rendered as an interactive ontology graph (asserted + inferred edges).

Run:  python examples/metaphysics_framework.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import (  # noqa: E402
    Individual,
    Instantiation,
    Reference,
    Relation,
    Universal,
    Value,
    Vocabulary,
    reasoning,
    visualize_relations,
)
from valuez.repository import ValueRepository  # noqa: E402

# A controlled vocabulary of the structural relations our ontology allows.
PREDICATES = Vocabulary(
    "metaphysical_relations",
    ["is-a", "part-of", "grounds"],
    reference=Reference("Framework convention", description="Allowed structural relations."),
)

SEP_UNIV = Reference("SEP, 'The Medieval Problem of Universals'")
SEP_PART = Reference("SEP, 'Mereology'")
SEP_GROUND = Reference("SEP, 'Metaphysical Grounding'")
ARISTOTLE = Reference("Aristotle, Categories")


def universals() -> list[Universal]:
    abstract = dict(ontological_status="abstract")
    return [
        Universal("LivingThing", ontological_status="fundamental",
                  definition="Highest kind in this ontology.", id="u_living", reference=ARISTOTLE),
        Universal("Animal", id="u_animal", reference=ARISTOTLE, **abstract),
        Universal("Mammal", id="u_mammal", **abstract),
        Universal("Human", definition="Rational animal.", id="u_human", reference=ARISTOTLE, **abstract),
        Universal("Colored", id="u_colored", **abstract),
        Universal("Red", id="u_red", **abstract),
        Universal("Scarlet", id="u_scarlet", **abstract),
    ]


def individuals() -> list[Individual]:
    concrete = dict(ontological_status="concrete")
    return [
        Individual("Socrates", id="i_socrates", reference=ARISTOTLE, **concrete),
        Individual("Plato", id="i_plato", **concrete),
        Individual("ThisApple", definition="A particular ripe apple.", id="i_apple", **concrete),
    ]


def instantiations() -> list[Instantiation]:
    return [
        Instantiation(Individual("Socrates"), Universal("Human"),
                      modality="necessary", id="inst_soc"),
        Instantiation(Individual("Plato"), Universal("Human"),
                      modality="necessary", id="inst_plato"),
        Instantiation(Individual("ThisApple"), Universal("Red"),
                      modality="contingent", id="inst_apple"),
    ]


def structural_relations() -> list[Relation]:
    v = PREDICATES
    return [
        # is-a: kind subsumption (a strict partial order).
        Relation("Human", "is-a", "Mammal", vocabulary=v, modality="necessary", id="isa_hm", reference=ARISTOTLE),
        Relation("Mammal", "is-a", "Animal", vocabulary=v, modality="necessary", id="isa_ma"),
        Relation("Animal", "is-a", "LivingThing", vocabulary=v, modality="necessary", id="isa_al"),
        Relation("Scarlet", "is-a", "Red", vocabulary=v, modality="necessary", id="isa_sr"),
        # part-of: structural mereology.
        Relation("Cell", "part-of", "Tissue", vocabulary=v, id="po_ct", reference=SEP_PART),
        Relation("Tissue", "part-of", "Organ", vocabulary=v, id="po_to"),
        Relation("Organ", "part-of", "Organism", vocabulary=v, id="po_oo"),
        # grounds: determinate grounds determinable (must be acyclic).
        Relation("Scarlet", "grounds", "Red", vocabulary=v, id="gr_sr", reference=SEP_GROUND),
        Relation("Red", "grounds", "Colored", vocabulary=v, id="gr_rc"),
    ]


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_metaphysics"))
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = ValueRepository(data_dir=out_dir / "store")

    us = universals()
    inds = individuals()
    insts = instantiations()
    rels = structural_relations()
    repo.add_values(us + inds + insts + rels)

    line = "-" * 72
    print(line)
    print("valuez example: a metaphysical framework (particulars, universals, orders)")
    print(line)
    print(f"Universals  ({len(us)}): " + ", ".join(f"{u.name}[{u.ontological_status}]" for u in us))
    print(f"Individuals ({len(inds)}): " + ", ".join(f"{i.name}[{i.ontological_status}]" for i in inds))
    print()
    print("Instantiation (Individual --instantiates--> Universal):")
    for inst in insts:
        print(f"  {inst.source} --{inst._edge_title()}--> {inst.target}")
    print()
    print("Structural relations:")
    for r in rels:
        print(f"  {r.source} --{r._edge_title()}--> {r.target}")
    print()

    # --- Reasoning: transitive closure of the two orders ------------------- #
    isa_inferred = reasoning.infer_transitive(
        rels, "is-a", reference=Reference("valuez.reasoning", description="Transitive closure of is-a."))
    part_inferred = reasoning.infer_transitive(
        rels, "part-of", reference=Reference("valuez.reasoning", description="Transitive closure of part-of."))
    print("Inferred is-a (transitive closure):")
    for r in isa_inferred:
        print(f"  {r.source} --is-a[inferred]--> {r.target}")
    print("Inferred part-of (transitive closure):")
    for r in part_inferred:
        print(f"  {r.source} --part-of[inferred]--> {r.target}")
    print()

    # --- Reasoning: grounding must be acyclic ------------------------------ #
    print(f"'grounds' is acyclic (well-formed strict order): {reasoning.is_acyclic(rels, 'grounds')}")
    broken = rels + [Relation("Colored", "grounds", "Scarlet", vocabulary=PREDICATES)]
    print(f"Adding 'Colored grounds Scarlet' -> acyclic? {reasoning.is_acyclic(broken, 'grounds')}")
    for cycle in reasoning.find_cycles(broken, "grounds"):
        print(f"  detected illicit grounding cycle: {' -> '.join(cycle + [cycle[0]])}")
    print()

    # --- Persistence + query through dotz ---------------------------------- #
    kinds = sorted(set(repo.query("[].kind")))
    total = len(repo.query("[]"))
    print(f"Persisted {total} values in dotz store; kinds: {kinds}")
    grounded = repo.query("[?reference] | length(@)")
    print(f"Ground-truthed (carry a Reference): {grounded} / {total}")

    graph_path = _render(insts + rels + isa_inferred + part_inferred, out_dir)
    if graph_path:
        print(f"Ontology graph: {graph_path}")
    print(line)


def _render(relations, out_dir: Path):
    try:
        import dotz.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)  # keep pyvis's vendored lib/ out of the working tree
        return visualize_relations(relations, "ontology_graph.html").resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
