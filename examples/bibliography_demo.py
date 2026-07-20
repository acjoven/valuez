"""Manage sources as BibTeX and share them across values.

This example shows the payoff of :class:`valuez.ReferenceRepository`: instead of
every value embedding its own copy of a citation string, sources live once in a
keyed, BibTeX-backed repository and values point at them by key. You can then
import/export ``.bib`` files and render a bibliography of everything an ontology
cites.

Run:  python examples/bibliography_demo.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Reading, ReferenceRepository, Scalar, Vocabulary  # noqa: E402

# A small BibTeX library (could equally be loaded from a .bib file on disk).
SOURCES = """
@book{incropera2007,
  author    = {Incropera, Frank P. and DeWitt, David P.},
  title     = {Fundamentals of Heat and Mass Transfer},
  edition   = {6},
  publisher = {Wiley},
  year      = {2007}
}
@book{kant1998,
  author    = {Kant, Immanuel},
  editor    = {Guyer, Paul and Wood, Allen W.},
  title     = {Critique of Pure Reason},
  publisher = {Cambridge University Press},
  year      = {1998}
}
@article{churchill1975,
  author  = {Churchill, Stuart W. and Chu, Humbert H. S.},
  title   = {Correlating equations for laminar and turbulent free convection},
  journal = {International Journal of Heat and Mass Transfer},
  volume  = {18},
  number  = {11},
  year    = {1975}
}
"""


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_bibliography"))
    out_dir.mkdir(parents=True, exist_ok=True)

    line = "-" * 72
    print(line)
    print("valuez bibliography: keyed sources shared across values")
    print(line)

    # 1) Load sources into a keyed repository.
    refs = ReferenceRepository()
    keys = refs.import_bibtex(SOURCES)
    print(f"Imported {len(keys)} sources: {', '.join(keys)}")
    print()

    # 2) Ground several values in ONE shared source (no citation duplication).
    incropera = refs.reference("incropera2007")
    h_free = [
        Scalar(2.0, unit="W/m^2/K", label="h_min", reference=incropera),
        Scalar(25.0, unit="W/m^2/K", label="h_max", reference=incropera),
    ]
    for s in h_free:
        assert s.reference is incropera  # same object, cited once
    print("Two heat-transfer values share a single keyed source:")
    print(f"  {h_free[0].label}={h_free[0].value}, {h_free[1].label}={h_free[1].value} "
          f"-> [{incropera.key}] {incropera.source}")
    print()

    # 3) A reading session can cite a repository source by key, too.
    book = Reading(source="Critique of Pure Reason",
                   predicates=Vocabulary("preds", ["is-form-of"]))
    with book.cite(refs.reference("kant1998")):
        book.universal("Space", "Pure a priori form of outer intuition.")
        book.universal("Intuition", "Immediate, singular representation.")
        book.relate("Space", "is-form-of", "Intuition")
    space = book.get("Space")
    print(f"Reading concept {space.name!r} is grounded in "
          f"[{space.reference.key}] {space.reference.entry_type}")
    print()

    # 4) Export the whole library and render a formatted bibliography.
    bib_path = out_dir / "sources.bib"
    refs.export_bibtex(bib_path)  # returns the BibTeX text; also writes the file
    print(f"BibTeX written: {bib_path}")
    print()
    print("Formatted bibliography (pybtex 'plain' style):")
    for key, text in sorted(refs.format_bibliography().items()):
        print(f"  [{key}] {text}")
    print(line)


if __name__ == "__main__":
    main()
