#!/usr/bin/env python3
"""Merge two ontologies into one universe by joining their common nodes.

This is the payoff of building `kant_ontology.py` and `kierkegaard.py` to the
same shape: two independently-authored maps that overlap by **name**. Merging
them is not concatenation -- `valuez.merge_ontologies` finds the shared nodes
(`Philosopher`, `Freedom`, `God`, ...) and *joins* them, so every edge from
either source attaches to the one shared node and the two graphs become a single
connected universe.

It then prints the merge report (which nodes were join points, which were genuine
semantic collisions), shows how a shared node now bridges both sources, exports
the merged universe, and renders two graphs: the whole universe and a legible
"seam" slice of just the edges incident to the join points.

Run:  python examples/merge_universe.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import merge_ontologies, visualize_relations  # noqa: E402

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _edges_touching(documents, name):
    """(from_kant, from_kierkegaard) edge ids incident to a joined node."""
    inc = [
        d for d in documents
        if d.get("kind") in ("relation", "instantiation")
        and name in (d.get("source"), d.get("target"))
    ]
    kant = [d["id"] for d in inc if d["id"].startswith("k_")]
    kier = [d["id"] for d in inc if d["id"].startswith("kk_")]
    return kant, kier


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_merge"))
    out_dir.mkdir(parents=True, exist_ok=True)

    result = merge_ontologies(
        [ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
        on_conflict="first",
    )

    line = "-" * 72
    print(line)
    print("valuez: merging Kant + Kierkegaard into one universe")
    print(line)
    print(result.report.summary())
    print()

    # Show that a joined node now bridges both source graphs.
    print("How the join stitches the two graphs together:")
    for name in ("Freedom", "God", "Philosopher"):
        kant, kier = _edges_touching(result.documents, name)
        print(f"  {name:14s} <- {len(kant)} edge(s) from Kant + {len(kier)} from Kierkegaard "
              f"now share one node")
    print()

    # Persist the merged universe and render it.
    universe = result.export(out_dir / "universe.json")
    print(f"Merged universe written: {universe}  ({result.report.output_total} docs)")

    graph = _render(result.relations(), out_dir, "universe.html")
    if graph:
        print(f"Universe graph: {graph}")

    # A legible "seam": only the edges incident to the join points -- this is the
    # connective tissue created by the merge.
    seam = result.bridges()
    joins = set(result.report.join_points)
    seam_path = _render(seam, out_dir, "universe_seam.html")
    if seam_path:
        print(f"Seam graph ({len(seam)} edges through {len(joins)} join points): {seam_path}")
    print(line)

    # Exact-name matching misses concepts the two traditions name differently.
    # A curated *alias* joins them: Kant's "Soul" (the thinking subject) and
    # Kierkegaard's "TheSelf" (a relation that relates itself to itself) are the
    # two systems' concept of the self. Declaring them equivalent folds them into
    # one node and rewires every edge from both sides onto it.
    print("Aligning by meaning with a curated alias (Soul = TheSelf):")
    aligned = merge_ontologies(
        [ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
        on_conflict="first",
        aliases=[["TheSelf", "Soul"]],
    )
    added = aligned.report.join_point_count - result.report.join_point_count
    kant, kier = _edges_touching(
        [d for d in aligned.documents], "TheSelf"
    )
    print(f"  join points {result.report.join_point_count} -> "
          f"{aligned.report.join_point_count} (+{added} via alias)")
    print(f"  canonical 'TheSelf' now carries {len(kant)} Kant + {len(kier)} "
          f"Kierkegaard edge(s); provenance = "
          f"{aligned.report.node_provenance.get('TheSelf')}")
    print(f"  cross-source bridges {result.report.bridge_edges} -> "
          f"{aligned.report.bridge_edges}")
    print(line)


def _render(relations, out_dir: Path, filename: str):
    try:
        import dotz.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        return visualize_relations(relations, filename).resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
