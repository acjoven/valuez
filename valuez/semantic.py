"""Semantic layer for valuez: concepts and the typed relations between them.

This is where valuez becomes a *semantic exploration* platform rather than just
a store of individual values:

- :class:`Concept` -- a named, ground-truthable abstract concept (a graph node).
- :class:`Relation` -- a typed, directed, ground-truthable edge between two
  concepts (``source`` --predicate--> ``target``), e.g. ``is-a`` / ``part-of``.

Both are :class:`~valuez.values.Value` subclasses, so they persist through
``dots`` storage like every other value. Because a :class:`Relation` serializes
with ``source`` / ``target`` fields, a collection of relations feeds directly
into ``dots``' directed-graph builder for visualization -- see
:func:`build_relation_graph` and :func:`visualize_relations`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, Optional, Union

from .qualitative import Qualitative
from .values import Reference, Value

__all__ = ["Concept", "Relation", "build_relation_graph", "visualize_relations"]

ConceptRef = Union[str, "Concept"]


def _concept_name(value: ConceptRef, field: str) -> str:
    """Coerce a Concept or string into the concept name used on edges."""
    if isinstance(value, Concept):
        return value.name
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field} must be a non-empty string or Concept")


class Concept(Qualitative):
    """A named abstract concept -- a node in the semantic graph."""

    kind: ClassVar[str] = "concept"

    def __init__(
        self,
        name: str,
        *,
        definition: Optional[str] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(name, str) or not name:
            raise ValueError("Concept.name must be a non-empty string")
        self.name = name
        self.definition = definition

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": self.name}
        if self.definition is not None:
            payload["definition"] = self.definition
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Concept":
        return cls(
            data["name"],
            definition=data.get("definition"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )


class Relation(Value):
    """A typed, directed edge between two concepts: ``source`` --predicate--> ``target``.

    ``source`` and ``target`` may be given as :class:`Concept` instances or plain
    concept names; they are stored as names so a set of relations maps cleanly
    onto a ``dots`` directed graph.
    """

    kind: ClassVar[str] = "relation"

    def __init__(
        self,
        source: ConceptRef,
        predicate: str,
        target: ConceptRef,
        *,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(predicate, str) or not predicate:
            raise ValueError("predicate must be a non-empty string")
        self.source = _concept_name(source, "source")
        self.target = _concept_name(target, "target")
        self.predicate = predicate

    def _payload(self) -> Dict[str, Any]:
        return {"source": self.source, "predicate": self.predicate, "target": self.target}

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Relation":
        return cls(
            data["source"],
            data["predicate"],
            data["target"],
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def __repr__(self) -> str:
        return f"Relation({self.source!r} -{self.predicate}-> {self.target!r})"


def build_relation_graph(relations: Iterable[Relation]) -> Any:
    """Build a ``networkx.DiGraph`` from relations, with predicates as edge labels."""
    import networkx as nx  # lazy: only needed for the graph layer

    graph = nx.DiGraph()
    for rel in relations:
        graph.add_node(rel.source, label=rel.source)
        graph.add_node(rel.target, label=rel.target)
        graph.add_edge(rel.source, rel.target, label=rel.predicate, title=rel.predicate)
    return graph


def visualize_relations(relations: Iterable[Relation], output_html: Union[str, Path]) -> Path:
    """Render relations to an interactive HTML graph via ``dots`` visualization."""
    from dots.graph import visualize_graph  # lazy: keeps dots optional at import

    graph = build_relation_graph(relations)
    return visualize_graph(graph, Path(output_html))
