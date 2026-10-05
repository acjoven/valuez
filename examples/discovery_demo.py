#!/usr/bin/env python3
"""Discover unexpected connections created by joining two ontologies.

Merging Kant and Kierkegaard by name stitches the maps at join points
(``Freedom``, ``God``, ``Existence``, ...). This example asks the next
question: which concepts that lived in *only one* source are now a short
walk from concepts that lived *only in the other*?

Those paths do not exist in either ontology alone -- they are an artifact
of the join. The walk is undirected, ranked shortest-first, and must pass
through at least one join point.

Run:  python examples/discovery_demo.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import discover, merge_ontologies  # noqa: E402

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"

# A 2-hop crossing that exists only after the join: Kant's doctrine of
# appearances grounds Freedom, and Kierkegaard's Anxiety is produced by it.
SHOWCASE = ("TranscendentalIdealism", "Anxiety")


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_discovery"))
    out_dir.mkdir(parents=True, exist_ok=True)

    universe = merge_ontologies(
        [ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
        on_conflict="first",
    )
    found = universe.discover(cutoff=2, limit=0)

    line = "-" * 72
    print(line)
    print("valuez discovery: unexpected paths across Kant + Kierkegaard")
    print(line)
    print(found.summary())
    print()

    start, end = SHOWCASE
    showcase = [
        c for c in found.crossings
        if {c.start, c.end} == {start, end}
    ]
    print(f"Showcase ({start} ~ {end}):")
    if showcase:
        for crossing in showcase:
            print(f"  {crossing.describe()}")
    else:
        print("  (no crossing at cutoff=2)")
    print()

    print(f"Kant -> Kierkegaard: {len(found.between('kant', 'kierkegaard'))}")
    print(f"Kierkegaard -> Kant: {len(found.between('kierkegaard', 'kant'))}")
    print()

    export = out_dir / "crossings.json"
    export.write_text(json.dumps(found.to_dict(), indent=2, sort_keys=True) + "\n")
    print(f"Discovery export: {export}  ({found.total} total, showing {len(found.crossings)})")

    graph = universe.graph()
    seeds = []
    for crossing in found.crossings[:12]:
        seeds.extend(crossing.path.nodes)
    # Unique, stable order.
    seen = []
    for name in seeds:
        if name not in seen and name in graph:
            seen.append(name)
    html_path = _render(graph.subgraph(seen), out_dir, "crossings.html")
    if html_path:
        print(f"Crossing subgraph ({len(seen)} nodes): {html_path}")
    print(line)


def _render(graph, out_dir: Path, filename: str):
    try:
        import dotz.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        return graph.visualize(filename).resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
