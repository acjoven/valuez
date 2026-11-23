#!/usr/bin/env python3
"""valuez in one screen: a sourced number and a small sourced concept map.

Both halves cite the same textbook, so every value here can be traced back to a
page. The concept map is built with the fluent ``Reading`` session:

- ``with book.at("Section 1.1"):`` cites a passage once; everything created in
  the block inherits that citation.
- ``book.concept(name, definition)`` is create-or-reuse, keyed by name.
- ``book.relate(src, pred, tgt)`` validates eagerly: both endpoints must already
  be declared and the predicate must be in the vocabulary.

Run:  python examples/quickstart.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Range, Reading, Reference, Vocabulary  # noqa: E402

TEXTBOOK = "Incropera & DeWitt, Fundamentals of Heat and Mass Transfer (6e)"


def sourced_number() -> Range:
    """A measured range that knows where it came from."""
    return Range(
        2, 25, unit="W/(m^2*K)", label="h, free convection in gases",
        reference=Reference(TEXTBOOK, locator="Table 1.1"),
    )


def build_reading() -> Reading:
    """The modes of heat transfer, as the textbook's first chapter lays them out."""
    book = Reading(source=TEXTBOOK, predicates=Vocabulary("relations", ["is-a"]))

    with book.at("Section 1.1"):
        book.concept("HeatTransfer", "Thermal energy in transit due to a temperature difference.")
        book.concept("Conduction", "Heat transfer across a stationary medium.")
        book.concept("Convection", "Heat transfer between a surface and a moving fluid.")
        book.concept("Radiation", "Energy emitted by a surface as electromagnetic waves.")
        for mode in ("Conduction", "Convection", "Radiation"):
            book.relate(mode, "is-a", "HeatTransfer")

    with book.at("Section 1.2.2"):
        book.concept("FreeConvection", "Convection driven by buoyancy in the fluid.")
        book.concept("ForcedConvection", "Convection driven by external means such as a fan or pump.")
        book.relate("FreeConvection", "is-a", "Convection")
        book.relate("ForcedConvection", "is-a", "Convection")

    return book


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_quickstart"))
    out_dir.mkdir(parents=True, exist_ok=True)

    h = sourced_number()
    print(f"{h.label}: {h.low} to {h.high} {h.unit}")
    print(f"  source: {h.reference.source}, {h.reference.locator}")
    print()

    book = build_reading()
    book.check()
    stats = book.stats()
    print(f"Concept map: {stats['concepts']} concepts, {stats['relations']} relations")

    free = book.get("FreeConvection")
    print(f"  {free.name} is cited at {free.reference.locator!r}")

    for edge in book.infer_transitive("is-a"):
        print(f"  inferred: {edge.source} is-a {edge.target}")

    print(f"  how FreeConvection relates to Radiation: "
          f"{book.graph().how('FreeConvection', 'Radiation')}")

    try:
        book.relate("FreeConvection", "is-a", "Advection")
    except ValueError as exc:
        print(f"  typo caught on entry: {exc}")
    print()

    ontology = book.export(out_dir / "quickstart.json", data_dir=out_dir / "store")
    print(f"Ontology written: {ontology}")

    try:
        import dotz.graph  # noqa: F401
        cwd = Path.cwd()
        try:
            os.chdir(out_dir)
            graph = book.render("quickstart.html", include_inferred="is-a")
            print(f"Graph: {graph.resolve()}")
        finally:
            os.chdir(cwd)
    except Exception as exc:  # pragma: no cover - visualization is optional
        print(f"(graph rendering skipped: {exc})")


if __name__ == "__main__":
    main()
