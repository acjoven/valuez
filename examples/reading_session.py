"""Build an ontology *as you read* with the fluent ``Reading`` session.

This is the ergonomic counterpart to ``examples/kant_ontology.py``. Where that
script hand-rolls id generation, de-duplication, and a referential-integrity
sweep around the raw ``Concept`` / ``Relation`` API, this one drives the same
kind of content through :class:`valuez.Reading` -- the Tier-1 authoring helper:

- ``with book.at("A51/B75"):`` cites a passage once; every concept, relation,
  and claim created in the block inherits that provenance automatically.
- ``book.universal(name, definition)`` is create-or-reuse: declaring a term
  twice returns the same node instead of duplicating it.
- ``book.relate(src, pred, tgt)`` validates *eagerly* -- both endpoints must
  already be declared and the predicate must be in the controlled vocabulary --
  so a typo raises immediately, at the line that introduced it.

It then validates, reasons over the graph, persists through ``dots``, and
renders an interactive graph. Run:  ``python examples/reading_session.py``
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Reading, Reference, Vocabulary  # noqa: E402

# The controlled predicate vocabulary: relate() rejects anything outside it.
PREDICATES = Vocabulary(
    "kantian_relations",
    ["is-a", "part-of", "wrote", "instantiates", "requires", "produces",
     "grounds", "applies-to", "is-form-of", "presupposes", "contrasts-with"],
    reference=Reference("Framework convention", description="Allowed relation types."),
)


def build_reading() -> Reading:
    """Reconstruct the epistemic core of the first Critique, passage by passage."""
    book = Reading(
        source="Kant, Critique of Pure Reason (Guyer & Wood, 1998)",
        predicates=PREDICATES,
        id_prefix="cpr_",
    )

    # Front matter: the author and the work (a typed instantiation edge).
    with book.at("title page"):
        book.individual("ImmanuelKant", "Prussian philosopher (1724-1804).",
                        ontological_status="historical")
        book.universal("Philosopher", "One who practices philosophy.",
                       ontological_status="abstract")
        book.universal("PhilosophicalWork", "A work of philosophy.",
                       ontological_status="abstract")
        book.individual("CritiqueOfPureReason", "Kant's first Critique (1781/1787).",
                        ontological_status="historical")
        book.instantiate("ImmanuelKant", "Philosopher")
        book.instantiate("CritiqueOfPureReason", "PhilosophicalWork")
        book.relate("ImmanuelKant", "wrote", "CritiqueOfPureReason")

    # Transcendental Aesthetic: sensibility, its forms, and intuition.
    with book.at("A19/B33"):
        book.universal("Sensibility", "Capacity to receive representations through affection.",
                       ontological_status="transcendental")
        book.universal("Intuition", "Immediate, singular representation of an object.",
                       ontological_status="transcendental")
        book.relate("Sensibility", "produces", "Intuition")
    with book.at("A22/B36"):
        book.universal("Space", "Pure a priori form of outer intuition.",
                       ontological_status="transcendental")
        book.universal("Time", "Pure a priori form of inner intuition.",
                       ontological_status="transcendental")
        book.relate("Space", "is-form-of", "Intuition")
        book.relate("Time", "is-form-of", "Intuition")
        book.claim("Space and time are pure a priori forms of intuition.",
                   truth_value=True, label="P-SpaceTime")

    # The Stufenleiter: intuitions and concepts are species of representation.
    with book.at("A320/B376"):
        book.universal("Representation", "Vorstellung: any mental content.",
                       ontological_status="transcendental")
        book.relate("Intuition", "is-a", "Representation")

    # Transcendental Analytic: understanding, concepts, categories.
    with book.at("A51/B75"):
        book.universal("Understanding", "Faculty of concepts and judgment.",
                       ontological_status="transcendental")
        book.universal("Concept", "General, mediate representation.",
                       ontological_status="transcendental")
        book.relate("Concept", "is-a", "Representation")
        book.universal("Cognition", "Objective, conscious representation of an object.",
                       ontological_status="transcendental")
        book.relate("Understanding", "produces", "Concept")
        book.relate("Cognition", "requires", "Intuition")
        book.relate("Cognition", "requires", "Concept")
        book.claim("Thoughts without content are empty, intuitions without concepts are blind.",
                   truth_value=True, label="P-EmptyBlind")
    with book.at("A80/B106"):
        book.universal("Category", "Pure a priori concept of the understanding.",
                       ontological_status="transcendental")
        book.universal("Experience", "Cognition through connected perceptions.",
                       ontological_status="phenomenal")
        book.relate("Category", "is-a", "Concept")
        book.relate("Understanding", "produces", "Category")
        book.relate("Category", "applies-to", "Experience")
        book.relate("Experience", "presupposes", "Category")

    # Transcendental Deduction: the argument tying categories to experience.
    with book.at("B131"):
        book.claim("The categories are conditions of the possibility of experience.",
                   truth_value=True, label="P-Categories")
        book.argue(
            ["Experience is possible only if its manifold is unified in one consciousness.",
             "That unity is possible only through the categories of the understanding."],
            "Therefore the categories are objectively valid conditions of all experience.",
            scheme="transcendental deduction", label="Transcendental-Deduction",
        )

    return book


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_reading"))
    out_dir.mkdir(parents=True, exist_ok=True)

    book = build_reading()
    book.check()  # eager validation already ran; this is the defensive sweep

    line = "-" * 72
    print(line)
    print("valuez reading session: the epistemic core of the first Critique")
    print(line)
    s = book.stats()
    print(f"Concepts    : {s['concepts']} "
          f"({s['individuals']} individuals, {s['universals']} universals)")
    print(f"Relations   : {s['relations']} (incl. {s['instantiations']} instantiations)")
    print(f"Propositions: {s['propositions']}   Arguments: {s['arguments']}")
    print("Referential integrity: OK")
    print()

    for pred in ("is-a", "grounds", "part-of"):
        print(f"  '{pred}' acyclic: {book.is_acyclic(pred)}")
    inferred = book.infer_transitive("is-a")
    print(f"  is-a transitive closure adds {len(inferred)} inferred edge(s):")
    for e in inferred:
        print(f"      {e.source} --is-a[inferred]--> {e.target}")
    print()

    # Show that provenance rode along automatically.
    space = book.get("Space")
    print(f"  Provenance example: {space.name} cited at "
          f"{space.reference.locator!r} in {space.reference.source!r}")
    print()

    ontology = book.export(out_dir / "reading_session.json", data_dir=out_dir / "store")
    print(f"Canonical ontology written: {ontology}")

    try:
        import dots.graph  # noqa: F401
        cwd = Path.cwd()
        try:
            os.chdir(out_dir)
            graph = book.render("reading_session.html", include_inferred="is-a")
            print(f"Ontology graph: {graph.resolve()}")
            args = book.render_arguments("reading_session_arguments.html")
            print(f"Argument map  : {args.resolve()}")
        finally:
            os.chdir(cwd)
    except Exception as exc:  # pragma: no cover - visualization is optional
        print(f"(graph rendering skipped: {exc})")
    print(line)


if __name__ == "__main__":
    main()
