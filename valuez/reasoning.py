"""Minimal structural reasoning over relations.

Many metaphysical (and semantic) predicates are *transitive strict partial
orders*: parthood (``part-of``), grounding (``grounds`` / ``depends-on``), and
kind subsumption (``is-a``). For those we usually want two things:

- the **transitive closure** -- every pair implied by chaining edges of one
  predicate -- and, conveniently, the *new* edges it entails
  (:func:`transitive_closure`, :func:`infer_transitive`);
- a **cycle check** -- such orders must be acyclic (nothing is part of, or
  grounds, itself, directly or transitively), so a cycle signals an illicit
  ontology (:func:`find_cycles`, :func:`is_acyclic`).

Everything operates on any iterable of :class:`~valuez.Relation` filtered by a
single ``predicate``, so the helpers are reusable well beyond metaphysics.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Optional, Set, Tuple

from .semantic import Relation
from .values import Reference

__all__ = [
    "build_predicate_digraph",
    "transitive_closure",
    "infer_transitive",
    "find_cycles",
    "is_acyclic",
]


def build_predicate_digraph(relations: Iterable[Relation], predicate: str) -> Any:
    """Build a ``networkx.DiGraph`` from the edges matching ``predicate``."""
    import networkx as nx

    graph = nx.DiGraph()
    for relation in relations:
        if relation.predicate == predicate:
            graph.add_edge(relation.source, relation.target)
    return graph


def transitive_closure(relations: Iterable[Relation], predicate: str) -> Set[Tuple[str, str]]:
    """Return all ``(source, target)`` pairs reachable via ``predicate`` chains.

    Includes directly-asserted edges; excludes reflexive ``(n, n)`` pairs unless
    ``n`` participates in a cycle (in which case it is reachable from itself).
    """
    import networkx as nx

    graph = build_predicate_digraph(relations, predicate)
    pairs: Set[Tuple[str, str]] = set()
    for node in graph.nodes:
        for descendant in nx.descendants(graph, node):
            pairs.add((node, descendant))
    return pairs


def infer_transitive(
    relations: Iterable[Relation],
    predicate: str,
    *,
    reference: Optional[Reference] = None,
) -> List[Relation]:
    """Return newly-entailed edges (closure minus explicit), as inferred Relations.

    Each returned :class:`~valuez.Relation` carries ``modality="inferred"`` so it
    is visually and semantically distinguishable from asserted edges. Reflexive
    pairs are omitted.
    """
    relations = list(relations)
    explicit = {(r.source, r.target) for r in relations if r.predicate == predicate}
    inferred: List[Relation] = []
    for source, target in sorted(transitive_closure(relations, predicate)):
        if source == target or (source, target) in explicit:
            continue
        inferred.append(
            Relation(source, predicate, target, modality="inferred", reference=reference)
        )
    return inferred


def find_cycles(relations: Iterable[Relation], predicate: str) -> List[List[str]]:
    """Return cycles among ``predicate`` edges (each as a list of node names)."""
    import networkx as nx

    graph = build_predicate_digraph(relations, predicate)
    return [list(cycle) for cycle in nx.simple_cycles(graph)]


def is_acyclic(relations: Iterable[Relation], predicate: str) -> bool:
    """Whether the ``predicate`` sub-graph is a DAG (as a strict order must be)."""
    import networkx as nx

    return nx.is_directed_acyclic_graph(build_predicate_digraph(relations, predicate))
