#!/usr/bin/env python3
"""Read a node: concept briefs over a single map and over a merged universe.

Storage, merge, and traversal make an ontology *queryable*. ``explain(node)``
makes one node of it *readable*: definition, immediate relations (with their
citations), the claims and arguments that bear on it, and the sources behind
all of that, grouped.

Two briefs are written as Markdown:

- ``Freedom`` in Kant's map alone;
- ``Freedom`` in the Kant + Kierkegaard universe, where the same page now draws
  on both authors' edges and sources.

Run:  python examples/concept_brief.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import explain, merge_ontologies  # noqa: E402

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_briefs"))
    out_dir.mkdir(parents=True, exist_ok=True)

    line = "-" * 72
    print(line)
    print("valuez concept briefs: read a node, not just query it")
    print(line)

    kant_docs = json.loads((ONTOLOGIES / "kant.json").read_text(encoding="utf-8"))
    kant = explain(kant_docs, "Freedom")
    print(kant.to_markdown())

    universe = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    merged = universe.explain("Freedom")
    print(line)
    print(f"Same node in the merged universe: {len(kant.relations)} -> {len(merged.relations)} "
          f"relations, {len(kant.sources())} -> {len(merged.sources())} sources")
    for src in merged.sources():
        print(f"  - {src}")
    print()

    kant_md = out_dir / "freedom_kant.md"
    merged_md = out_dir / "freedom_universe.md"
    kant_md.write_text(kant.to_markdown(), encoding="utf-8")
    merged_md.write_text(merged.to_markdown(), encoding="utf-8")
    (out_dir / "freedom_universe.json").write_text(
        json.dumps(merged.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Briefs written: {kant_md}, {merged_md}")
    print(line)


if __name__ == "__main__":
    main()
