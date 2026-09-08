"""Concept briefs: a readable page for any node in an ontology.

Storage, merge, and traversal make a map *queryable*; a brief makes one node of
it *readable*. :func:`explain` assembles, for a concept name:

- the node itself (kind, definition, ``ontological_status``);
- its immediate relations, outgoing and incoming, with modality / strength;
- the propositions and arguments that bear on it;
- every citation behind those items, grouped by source.

Like :mod:`valuez.traversal`, this is mechanics over asserted content. Nothing
is inferred or invented. The one heuristic -- *mentions*, where a proposition,
argument, or another concept's definition names this concept in its text -- is
plain word-boundary matching and is labelled as a mention wherever it surfaces,
so a reader can tell an asserted edge from a textual hit.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .semantic import Argument, Concept, Proposition, Relation
from .values import Reference, Value

__all__ = ["Brief", "explain"]

ConceptRef = Union[str, Concept]


def _node_name(value: ConceptRef) -> str:
    if isinstance(value, Concept):
        return value.name
    if isinstance(value, str) and value:
        return value
    raise ValueError("node must be a non-empty string or Concept")


def _split_camel(name: str) -> str:
    """``MoralLaw`` -> ``Moral Law`` so prose mentions match CamelCase names."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def _mention_pattern(name: str) -> "re.Pattern[str]":
    forms = {name, _split_camel(name)}
    alternation = "|".join(re.escape(f) for f in sorted(forms, key=len, reverse=True))
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alternation})(?![A-Za-z0-9])", re.IGNORECASE)


def _ref_key(ref: Reference) -> str:
    return json.dumps(ref.to_dict(), sort_keys=True)


def _edge_sort(rel: Relation) -> Tuple[str, str, str, str]:
    return (rel.predicate, rel.source, rel.target, rel.id)


def _edge_title(rel: Relation) -> str:
    parts = [rel.predicate]
    if rel.modality:
        parts.append(f"[{rel.modality}]")
    if rel.strength is not None:
        parts.append(f"({rel.strength:g})")
    return " ".join(parts)


def _cite(ref: Optional[Reference]) -> str:
    if ref is None:
        return ""
    if ref.locator:
        return f"{ref.source}, {ref.locator}"
    return ref.source


class Brief:
    """The assembled page for one node. Build one with :func:`explain`.

    Fields are plain lists of the underlying values, so a brief is also a
    convenient *slice* of the ontology: :meth:`values` returns everything it
    drew on, and :meth:`bibliography` collects the sources behind that slice.
    """

    def __init__(
        self,
        name: str,
        *,
        node: Optional[Concept],
        outgoing: Sequence[Relation],
        incoming: Sequence[Relation],
        propositions: Sequence[Tuple[Proposition, str]],
        arguments: Sequence[Tuple[Argument, str]],
        mentioned_in: Sequence[Concept],
    ) -> None:
        self.name = name
        self.node = node
        self.outgoing: Tuple[Relation, ...] = tuple(sorted(outgoing, key=_edge_sort))
        self.incoming: Tuple[Relation, ...] = tuple(sorted(incoming, key=_edge_sort))
        # (value, how) where how is "edge" (an asserted relation touches the
        # value's handle) or "mention" (the value's text names this concept).
        self.propositions: Tuple[Tuple[Proposition, str], ...] = tuple(propositions)
        self.arguments: Tuple[Tuple[Argument, str], ...] = tuple(arguments)
        self.mentioned_in: Tuple[Concept, ...] = tuple(
            sorted(mentioned_in, key=lambda c: c.name)
        )

    # ------------------------------------------------------------------ #
    # Convenience accessors                                               #
    # ------------------------------------------------------------------ #
    @property
    def kind(self) -> Optional[str]:
        return self.node.kind if self.node is not None else None

    @property
    def definition(self) -> Optional[str]:
        return self.node.definition if self.node is not None else None

    @property
    def ontological_status(self) -> Optional[str]:
        return getattr(self.node, "ontological_status", None)

    @property
    def relations(self) -> Tuple[Relation, ...]:
        return self.outgoing + self.incoming

    @property
    def neighbors(self) -> Tuple[str, ...]:
        names = {r.target for r in self.outgoing} | {r.source for r in self.incoming}
        names.discard(self.name)
        return tuple(sorted(names))

    def by_predicate(self, direction: str = "out") -> Dict[str, List[str]]:
        """``{predicate: [other endpoint, ...]}`` for one direction."""
        if direction not in ("out", "in"):
            raise ValueError("direction must be 'out' or 'in'")
        edges = self.outgoing if direction == "out" else self.incoming
        out: Dict[str, List[str]] = {}
        for rel in edges:
            other = rel.target if direction == "out" else rel.source
            bucket = out.setdefault(rel.predicate, [])
            if other not in bucket:
                bucket.append(other)
        return out

    def values(self) -> List[Value]:
        """Every value this brief drew on (node, edges, claims, arguments)."""
        out: List[Value] = []
        if self.node is not None:
            out.append(self.node)
        out.extend(self.outgoing)
        out.extend(self.incoming)
        out.extend(p for p, _ in self.propositions)
        out.extend(a for a, _ in self.arguments)
        out.extend(self.mentioned_in)
        return out

    def citations(self) -> List[Reference]:
        """Distinct references behind the brief, node first, then edges, claims, arguments."""
        seen: Dict[str, Reference] = {}
        for value in self.values():
            ref = value.reference
            if ref is not None:
                seen.setdefault(_ref_key(ref), ref)
        return list(seen.values())

    def sources(self) -> Dict[str, List[str]]:
        """Citations grouped by ``source`` -> sorted distinct locators."""
        grouped: Dict[str, List[str]] = {}
        for ref in self.citations():
            locs = grouped.setdefault(ref.source, [])
            if ref.locator and ref.locator not in locs:
                locs.append(ref.locator)
        return {src: sorted(locs) for src, locs in sorted(grouped.items())}

    def bibliography(self, **kwargs: Any) -> Any:
        """A :class:`~valuez.ReferenceRepository` of the sources behind this brief.

        Passage-only references are included by default (``include_unkeyed=True``),
        since a brief is about *what was cited*, not only keyed BibTeX sources.
        """
        from .bibliography import ReferenceRepository

        kwargs.setdefault("include_unkeyed", True)
        return ReferenceRepository.from_values(self.citations(), **kwargs)

    def is_empty(self) -> bool:
        return (
            self.node is None
            and not self.outgoing
            and not self.incoming
            and not self.propositions
            and not self.arguments
            and not self.mentioned_in
        )

    # ------------------------------------------------------------------ #
    # Rendering                                                           #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "definition": self.definition,
            "ontological_status": self.ontological_status,
            "node": self.node.to_dict() if self.node is not None else None,
            "outgoing": [r.to_dict() for r in self.outgoing],
            "incoming": [r.to_dict() for r in self.incoming],
            "propositions": [
                {"how": how, **p.to_dict()} for p, how in self.propositions
            ],
            "arguments": [{"how": how, **a.to_dict()} for a, how in self.arguments],
            "mentioned_in": [c.name for c in self.mentioned_in],
            "sources": self.sources(),
        }

    def to_markdown(self) -> str:
        lines: List[str] = [f"# {self.name}"]
        meta = [m for m in (self.kind, self.ontological_status) if m]
        if meta:
            lines.append(f"*{' · '.join(meta)}*")
        if self.node is not None and self.node.reference is not None:
            lines.append(f"Cited: {_cite(self.node.reference)}")
        if self.definition:
            lines.append("")
            lines.append(self.definition)

        if self.outgoing or self.incoming:
            lines.append("")
            lines.append("## Relations")
            for rel in self.outgoing:
                lines.append(self._edge_line(rel, out=True))
            for rel in self.incoming:
                lines.append(self._edge_line(rel, out=False))

        if self.propositions:
            lines.append("")
            lines.append("## Claims")
            for prop, how in self.propositions:
                tv = ""
                if prop.truth_value is True:
                    tv = " (asserted)"
                elif prop.truth_value is False:
                    tv = " (denied)"
                handle = f"**{prop.label}** — " if prop.label else ""
                lines.append(f"- {handle}{prop.statement}{tv}{self._tail(prop.reference, how)}")

        if self.arguments:
            lines.append("")
            lines.append("## Arguments")
            for arg, how in self.arguments:
                scheme = f" [{arg.scheme}]" if arg.scheme else ""
                lines.append(f"- **{arg.handle}**{scheme}{self._tail(arg.reference, how)}")
                for premise in arg.premises:
                    lines.append(f"    - {premise}")
                lines.append(f"    - ⇒ {arg.conclusion}")

        if self.mentioned_in:
            lines.append("")
            lines.append("## Mentioned in definitions of")
            lines.append("- " + ", ".join(c.name for c in self.mentioned_in))

        sources = self.sources()
        if sources:
            lines.append("")
            lines.append("## Sources")
            for src, locs in sources.items():
                suffix = f" — {', '.join(locs)}" if locs else ""
                lines.append(f"- {src}{suffix}")
        return "\n".join(lines) + "\n"

    def _edge_line(self, rel: Relation, *, out: bool) -> str:
        title = _edge_title(rel)
        if out:
            text = f"- {self.name} —{title}→ {rel.target}"
        else:
            text = f"- {rel.source} —{title}→ {self.name}"
        cite = _cite(rel.reference)
        return f"{text}  ({cite})" if cite else text

    @staticmethod
    def _tail(ref: Optional[Reference], how: str) -> str:
        bits = []
        cite = _cite(ref)
        if cite:
            bits.append(cite)
        if how == "mention":
            bits.append("mention")
        return f"  ({'; '.join(bits)})" if bits else ""

    def __str__(self) -> str:
        return self.to_markdown()

    def __repr__(self) -> str:
        return (
            f"Brief({self.name!r}, kind={self.kind!r}, relations={len(self.relations)}, "
            f"claims={len(self.propositions)}, arguments={len(self.arguments)})"
        )


def explain(
    values: Iterable[Union[Value, Dict[str, Any]]],
    node: ConceptRef,
    *,
    mentions: bool = True,
) -> Brief:
    """Assemble a :class:`Brief` for ``node`` from an ontology's values.

    ``values`` may be :class:`~valuez.values.Value` objects or stored document
    dicts (a ``Reading.values()``, a ``ValueRepository.query("[]")``, a merged
    universe's ``documents``, ...). ``mentions=False`` restricts claims and
    arguments to those attached by an asserted edge.

    Raises ``ValueError`` when the name is neither a declared node nor an edge
    endpoint anywhere in ``values``.
    """
    name = _node_name(node)

    concepts: List[Concept] = []
    relations: List[Relation] = []
    propositions: List[Proposition] = []
    arguments: List[Argument] = []
    for item in values:
        value = item if isinstance(item, Value) else Value.from_dict(item)
        if isinstance(value, Relation):
            relations.append(value)
        elif isinstance(value, Concept):
            concepts.append(value)
        elif isinstance(value, Proposition):
            propositions.append(value)
        elif isinstance(value, Argument):
            arguments.append(value)

    target: Optional[Concept] = next((c for c in concepts if c.name == name), None)
    outgoing = [r for r in relations if r.source == name]
    incoming = [r for r in relations if r.target == name]
    if target is None and not outgoing and not incoming:
        raise ValueError(f"unknown node {name!r}")

    # Claims / arguments attached by an asserted edge to their handle.
    touched = {r.target for r in outgoing} | {r.source for r in incoming}
    prop_hits: Dict[str, Tuple[Proposition, str]] = {}
    arg_hits: Dict[str, Tuple[Argument, str]] = {}
    for prop in propositions:
        if prop.handle in touched:
            prop_hits.setdefault(prop.id, (prop, "edge"))
    for arg in arguments:
        if arg.handle in touched:
            arg_hits.setdefault(arg.id, (arg, "edge"))

    mentioned_in: List[Concept] = []
    if mentions:
        pattern = _mention_pattern(name)
        for prop in propositions:
            if prop.id not in prop_hits and pattern.search(prop.statement):
                prop_hits[prop.id] = (prop, "mention")
        for arg in arguments:
            if arg.id in arg_hits:
                continue
            texts = list(arg.premises) + [arg.conclusion]
            if any(pattern.search(t) for t in texts):
                arg_hits[arg.id] = (arg, "mention")
        for concept in concepts:
            if concept.name != name and concept.definition and pattern.search(concept.definition):
                mentioned_in.append(concept)

    # Keep the ontology's own ordering for claims and arguments.
    ordered_props = [prop_hits[p.id] for p in propositions if p.id in prop_hits]
    ordered_args = [arg_hits[a.id] for a in arguments if a.id in arg_hits]

    return Brief(
        name,
        node=target,
        outgoing=outgoing,
        incoming=incoming,
        propositions=ordered_props,
        arguments=ordered_args,
        mentioned_in=mentioned_in,
    )
