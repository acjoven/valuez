#!/usr/bin/env python3
"""Walk a stored ontology: neighborhoods, paths, and topic subgraphs.

The capture/structure side of valuez can already persist a map and render it.
This example is the first *exploration* slice: given a graph, ask

- what sits next to this node?
- how does A relate to B?
- what is the topic around these seeds?

It runs the same questions against a tiny fluent ``Reading`` session *and*
the committed Kant ontology, then writes a topic-subgraph HTML for Freedom.

Run:  python examples/traversal_demo.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Graph, Reading, Vocabulary  # noqa: E402

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _print_path(label: str, path) -> None:
    if path is None:
        print(f"  {label}: (no path)")
    else:
        print(f"  {label}: {path.describe()}   [{path.length} hop(s)]")


def _print_neighborhood(g: Graph, name: str, hops: int = 1) -> None:
    nb = g.neighborhood(name, hops=hops)
    others = [n for n in nb.nodes if n != name]
    print(f"  {name} ({hops}-hop): {len(others)} neighbor(s), {len(nb.relations)} edge(s)")
    for rel in nb.relations:
        print(f"      {rel.source} -{rel.predicate}-> {rel.target}")


def _tiny_session() -> Reading:
    book = Reading(
        source="Kant, Critique of Pure Reason",
        predicates=Vocabulary("preds", ["is-a", "is-form-of", "produces"]),
        id_prefix="demo_",
    )
    with book.at("A22/B36"):
        book.universal("Space", "Pure a priori form of outer intuition.")
        book.universal("Intuition", "Immediate, singular representation.")
        book.universal("Representation", "Vorstellung: any mental content.")
        book.universal("Concept", "General, mediate representation.")
        book.universal("Understanding", "Faculty of concepts and judgment.")
        book.relate("Space", "is-form-of", "Intuition")
        book.relate("Intuition", "is-a", "Representation")
        book.relate("Concept", "is-a", "Representation")
        book.relate("Understanding", "produces", "Concept")
    return book


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_traversal"))
    out_dir.mkdir(parents=True, exist_ok=True)

    line = "-" * 72
    print(line)
    print("valuez traversal: neighborhoods, paths, topic subgraphs")
    print(line)

    # --- Small session ------------------------------------------------- #
    book = _tiny_session()
    g = book.graph()
    print(f"Reading session graph: {g.n_nodes} nodes, {g.n_edges} edges")
    _print_path("how Space relates to Representation", g.how("Space", "Representation"))
    _print_path("how Concept relates to Intuition (undirected)", g.how("Concept", "Intuition"))
    _print_path("shortest directed Concept -> Intuition",
                g.shortest_path("Concept", "Intuition", directed=True))
    print()
    print("Neighborhood of Understanding:")
    _print_neighborhood(g, "Understanding", hops=1)
    print()

    topic = g.topic("Representation", hops=1)
    print(f"Topic subgraph around Representation (1 hop): {topic.n_nodes} nodes, {topic.n_edges} edges")
    print(f"  nodes: {', '.join(topic.nodes)}")
    print()

    # --- Kant ontology ------------------------------------------------- #
    kant = Graph.from_ontology(ONTOLOGIES / "kant.json")
    print(f"Kant ontology graph: {kant.n_nodes} nodes, {kant.n_edges} edges")
    _print_path("how Space relates to Intuition", kant.how("Space", "Intuition"))
    _print_path("how Freedom relates to MoralLaw", kant.how("Freedom", "MoralLaw"))
    print()
    print("Neighborhood of Freedom:")
    _print_neighborhood(kant, "Freedom", hops=1)
    print()

    freedom = kant.topic("Freedom", hops=1)
    print(f"Freedom topic subgraph: {freedom.n_nodes} nodes, {freedom.n_edges} edges")

    try:
        import dotz.graph  # noqa: F401
        cwd = Path.cwd()
        try:
            os.chdir(out_dir)
            html = freedom.visualize("freedom_topic.html")
            print(f"Freedom topic graph: {html.resolve()}")
        finally:
            os.chdir(cwd)
    except Exception as exc:  # pragma: no cover - visualization is optional
        print(f"(graph rendering skipped: {exc})")
    print(line)


if __name__ == "__main__":
    main()
