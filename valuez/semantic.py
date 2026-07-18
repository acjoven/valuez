"""Semantic layer for valuez: concepts and the typed relations between them.

This is where valuez becomes a *semantic exploration* platform rather than just
a store of individual values:

- :class:`Concept` -- a named, ground-truthable abstract concept (a graph node).
- :class:`Relation` -- a typed, directed, ground-truthable edge between two
  concepts (``source`` --predicate--> ``target``), e.g. ``is-a`` / ``part-of``.
  Predicates may be constrained to a :class:`~valuez.Vocabulary`, and each
  relation may carry a ``modality`` (e.g. ``necessary`` / ``defeasible``) and a
  ``strength`` in ``[0, 1]``.
- :class:`Proposition` -- a reified, truth-apt statement (a claim that can be
  cited, asserted/denied, and disputed).
- :class:`Argument` -- a set of premises supporting a conclusion; arguments can
  ``support`` / ``attack`` each other and other propositions (Dung-style).

These are :class:`~valuez.values.Value` subclasses, so they persist through
``dots`` storage like every other value. Because a :class:`Relation` serializes
with ``source`` / ``target`` fields, a collection of relations feeds directly
into ``dots``' directed-graph builder for visualization -- see
:func:`build_relation_graph`, :func:`visualize_relations`,
:func:`build_argument_graph`, and :func:`visualize_arguments`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Union

from .qualitative import Qualitative, Vocabulary
from .values import Reference, Value

__all__ = [
    "Concept",
    "Relation",
    "Proposition",
    "Argument",
    "build_relation_graph",
    "visualize_relations",
    "build_argument_graph",
    "visualize_arguments",
]

ConceptRef = Union[str, "Concept"]
PropositionRef = Union[str, "Proposition"]


def _concept_name(value: ConceptRef, field: str) -> str:
    """Coerce a Concept or string into the concept name used on edges."""
    if isinstance(value, Concept):
        return value.name
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field} must be a non-empty string or Concept")


def _proposition_handle(value: PropositionRef, field: str) -> str:
    """Coerce a Proposition or string into the handle used on argument edges."""
    if isinstance(value, Proposition):
        return value.handle
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field} must be a non-empty string or Proposition")


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

    The ``predicate`` may be constrained to a :class:`~valuez.Vocabulary` for
    rigour, and the edge may carry a ``modality`` (e.g. ``necessary``,
    ``defeasible``) and a ``strength`` in ``[0, 1]``.
    """

    kind: ClassVar[str] = "relation"

    def __init__(
        self,
        source: ConceptRef,
        predicate: str,
        target: ConceptRef,
        *,
        vocabulary: Optional[Vocabulary] = None,
        modality: Optional[str] = None,
        strength: Optional[float] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(predicate, str) or not predicate:
            raise ValueError("predicate must be a non-empty string")
        if vocabulary is not None:
            if not isinstance(vocabulary, Vocabulary):
                raise TypeError("vocabulary must be a Vocabulary instance or None")
            if not vocabulary.contains(predicate):
                raise ValueError(
                    f"predicate {predicate!r} is not in vocabulary {vocabulary.name!r}"
                )
        if modality is not None and (not isinstance(modality, str) or not modality):
            raise ValueError("modality must be a non-empty string or None")
        if strength is not None:
            if isinstance(strength, bool) or not isinstance(strength, (int, float)):
                raise TypeError("strength must be a real number or None")
            if not (0.0 <= float(strength) <= 1.0):
                raise ValueError("strength must be within [0, 1]")
        self.source = _concept_name(source, "source")
        self.target = _concept_name(target, "target")
        self.predicate = predicate
        self.vocabulary = vocabulary
        self.modality = modality
        self.strength = float(strength) if strength is not None else None

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "source": self.source,
            "predicate": self.predicate,
            "target": self.target,
        }
        if self.modality is not None:
            payload["modality"] = self.modality
        if self.strength is not None:
            payload["strength"] = self.strength
        if self.vocabulary is not None:
            payload["predicate_vocabulary"] = self.vocabulary.to_dict()
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Relation":
        vocab = data.get("predicate_vocabulary")
        return cls(
            data["source"],
            data["predicate"],
            data["target"],
            vocabulary=Vocabulary.from_dict(vocab) if vocab else None,
            modality=data.get("modality"),
            strength=data.get("strength"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def _edge_title(self) -> str:
        parts = [self.predicate]
        if self.modality:
            parts.append(f"[{self.modality}]")
        if self.strength is not None:
            parts.append(f"({self.strength:g})")
        return " ".join(parts)

    def __repr__(self) -> str:
        mod = f" [{self.modality}]" if self.modality else ""
        return f"Relation({self.source!r} -{self.predicate}{mod}-> {self.target!r})"


def build_relation_graph(relations: Iterable[Relation]) -> Any:
    """Build a ``networkx.DiGraph`` from relations, with predicates as edge labels."""
    import networkx as nx  # lazy: only needed for the graph layer

    graph = nx.DiGraph()
    for rel in relations:
        graph.add_node(rel.source, label=rel.source)
        graph.add_node(rel.target, label=rel.target)
        graph.add_edge(rel.source, rel.target, label=rel.predicate, title=rel._edge_title())
    return graph


def visualize_relations(relations: Iterable[Relation], output_html: Union[str, Path]) -> Path:
    """Render relations to an interactive HTML graph via ``dots`` visualization."""
    from dots.graph import visualize_graph  # lazy: keeps dots optional at import

    graph = build_relation_graph(relations)
    return visualize_graph(graph, Path(output_html))


class Proposition(Qualitative):
    """A reified, truth-apt statement -- a claim that can be cited and disputed.

    ``truth_value`` is optional: ``True``/``False`` records an asserted stance,
    while ``None`` leaves the claim open/unasserted.
    """

    kind: ClassVar[str] = "proposition"

    def __init__(
        self,
        statement: str,
        *,
        truth_value: Optional[bool] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(statement, str) or not statement:
            raise ValueError("Proposition.statement must be a non-empty string")
        if truth_value is not None and not isinstance(truth_value, bool):
            raise TypeError("truth_value must be a bool or None")
        self.statement = statement
        self.truth_value = truth_value

    @property
    def handle(self) -> str:
        """Short identifier used as a graph node (``label`` if set, else statement)."""
        return self.label or self.statement

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"statement": self.statement}
        if self.truth_value is not None:
            payload["truth_value"] = self.truth_value
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Proposition":
        return cls(
            data["statement"],
            truth_value=data.get("truth_value"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )


class Argument(Value):
    """A set of premises supporting a conclusion.

    Premises and conclusion may be given as :class:`Proposition` instances or
    plain handles (strings); they are stored as handles so an argument maps onto
    a ``dots`` graph. ``scheme`` optionally names the argumentation scheme
    (e.g. ``modus-ponens``, ``reductio``).
    """

    kind: ClassVar[str] = "argument"

    def __init__(
        self,
        premises: Iterable[PropositionRef],
        conclusion: PropositionRef,
        *,
        scheme: Optional[str] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        self.premises: List[str] = [_proposition_handle(p, "premise") for p in premises]
        if not self.premises:
            raise ValueError("Argument requires at least one premise")
        self.conclusion = _proposition_handle(conclusion, "conclusion")
        if scheme is not None and (not isinstance(scheme, str) or not scheme):
            raise ValueError("scheme must be a non-empty string or None")
        self.scheme = scheme

    @property
    def handle(self) -> str:
        """Graph node identifier for the argument (``label`` if set, else ``id``)."""
        return self.label or self.id

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "premises": list(self.premises),
            "conclusion": self.conclusion,
        }
        if self.scheme is not None:
            payload["scheme"] = self.scheme
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Argument":
        return cls(
            data["premises"],
            data["conclusion"],
            scheme=data.get("scheme"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def __repr__(self) -> str:
        return f"Argument(premises={self.premises!r} => {self.conclusion!r})"


def build_argument_graph(
    arguments: Iterable[Argument],
    relations: Iterable[Relation] = (),
) -> Any:
    """Build a ``networkx.DiGraph`` argument map.

    For each argument: ``premise --premise--> argument --concludes--> conclusion``.
    Any additional ``relations`` (e.g. ``supports`` / ``attacks`` between
    arguments or propositions) are overlaid on the same graph.
    """
    import networkx as nx  # lazy: only needed for the graph layer

    graph = nx.DiGraph()
    for arg in arguments:
        aname = arg.handle
        graph.add_node(aname, label=aname, kind="argument")
        for premise in arg.premises:
            graph.add_node(premise, label=premise, kind="proposition")
            graph.add_edge(premise, aname, label="premise", title="premise")
        graph.add_node(arg.conclusion, label=arg.conclusion, kind="proposition")
        graph.add_edge(aname, arg.conclusion, label="concludes", title="concludes")
    for rel in relations:
        graph.add_node(rel.source, label=rel.source)
        graph.add_node(rel.target, label=rel.target)
        graph.add_edge(rel.source, rel.target, label=rel.predicate, title=rel._edge_title())
    return graph


def visualize_arguments(
    arguments: Iterable[Argument],
    output_html: Union[str, Path],
    relations: Iterable[Relation] = (),
) -> Path:
    """Render an argument map to interactive HTML via ``dots`` visualization."""
    from dots.graph import visualize_graph  # lazy: keeps dots optional at import

    graph = build_argument_graph(arguments, relations)
    return visualize_graph(graph, Path(output_html))
