"""Inference and tension detection over a valuez ontology.

:mod:`valuez.reasoning` is the structural-order primitive (transitive closure
and cycles of one predicate). This module **generalizes** that into one pass
over a whole ontology:

- **typed forward-chaining rules** that emit *derived* relations, each carrying
  a :class:`~valuez.values.Reference` that names the rule and the asserted
  edges it rested on (``metadata["because"]``);
- **tensions** -- illicit cycles, predicate clashes (``contrasts-with`` vs
  ``is-a``), and contradictory truth-values;
- **gaps** -- dangling endpoints, isolated or undefined nodes, open questions,
  missing argument premises;
- **Dung grounded acceptability** of arguments under ``attacks``.

Derived items are *returned*, never written into the canonical graph. Meaning-
bearing content still enters only through a human-reviewed path; this layer is
mechanics, like traversal and briefs.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from .metaphysics import Instantiation
from .semantic import Argument, Concept, Proposition, Relation
from .values import Reference, Value
from . import reasoning

__all__ = [
    "Derivation",
    "Finding",
    "Analysis",
    "analyze",
    "TRANSITIVE_PREDICATES",
    "SYMMETRIC_PREDICATES",
    "DERIVED_SOURCE",
]

DERIVED_SOURCE = "valuez.analysis"

# Strict partial orders: transitive, and a cycle is a tension.
TRANSITIVE_PREDICATES = ("is-a", "part-of", "grounds", "presupposes", "requires")
SYMMETRIC_PREDICATES = ("contrasts-with", "contradicts")
# An asserted (or derived) edge of the first predicate clashes with one of the second
# between the same two nodes, in either direction.
_CLASH_PAIRS = (
    ("contrasts-with", "is-a"),
    ("contrasts-with", "instantiates"),
    ("contrasts-with", "part-of"),
    ("contrasts-with", "grounds"),
    ("contradicts", "is-a"),
    ("contradicts", "instantiates"),
    ("attacks", "supports"),
)

PredicateSpec = Optional[Union[str, Iterable[str]]]


def _as_tuple(spec: PredicateSpec, default: Tuple[str, ...]) -> Tuple[str, ...]:
    if spec is None:
        return default
    if isinstance(spec, str):
        if not spec:
            raise ValueError("predicate list must not be empty")
        return (spec,)
    out = tuple(spec)
    if any(not isinstance(p, str) or not p for p in out):
        raise ValueError("predicates must be non-empty strings")
    return out


def _hydrate(values: Iterable[Union[Value, Dict[str, Any]]]) -> List[Value]:
    out: List[Value] = []
    for item in values:
        out.append(item if isinstance(item, Value) else Value.from_dict(item))
    return out


def _edge_key(rel: Relation) -> Tuple[str, str, str]:
    return (rel.source, rel.predicate, rel.target)


def _derived_ref(rule: str, description: str, because: Sequence[str]) -> Reference:
    return Reference(
        DERIVED_SOURCE,
        description=description,
        metadata={"rule": rule, "because": list(because)},
    )


def _path_because(
    relations: Sequence[Relation],
    predicate: str,
    source: str,
    target: str,
) -> List[str]:
    """Ids of asserted ``predicate`` edges along a shortest path source -> target."""
    import networkx as nx

    graph = reasoning.build_predicate_digraph(relations, predicate)
    try:
        nodes = nx.shortest_path(graph, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []
    by_pair: Dict[Tuple[str, str], str] = {}
    for rel in relations:
        if rel.predicate == predicate:
            by_pair.setdefault((rel.source, rel.target), rel.id)
    return [by_pair[pair] for a, b in zip(nodes, nodes[1:]) if (pair := (a, b)) in by_pair]


class Derivation:
    """One inferred edge plus the rule and asserted ids that produced it."""

    def __init__(self, rule: str, relation: Relation, because: Sequence[str] = ()) -> None:
        self.rule = rule
        self.relation = relation
        self.because = tuple(because)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "because": list(self.because),
            "relation": self.relation.to_dict(),
        }

    def __repr__(self) -> str:
        r = self.relation
        return f"Derivation({self.rule}: {r.source} -{r.predicate}-> {r.target})"


class Finding:
    """A tension or a gap. ``kind`` is a stable machine key; ``detail`` is readable."""

    def __init__(self, kind: str, detail: str, items: Sequence[str] = ()) -> None:
        self.kind = kind
        self.detail = detail
        self.items = tuple(items)

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "detail": self.detail, "items": list(self.items)}

    def __repr__(self) -> str:
        return f"Finding({self.kind}: {self.detail})"


class Analysis:
    """The result of :func:`analyze`: derived edges, tensions, gaps, argument statuses."""

    def __init__(
        self,
        *,
        derived: Sequence[Derivation] = (),
        tensions: Sequence[Finding] = (),
        gaps: Sequence[Finding] = (),
        arguments: Optional[Dict[str, str]] = None,
    ) -> None:
        self.derived: Tuple[Derivation, ...] = tuple(derived)
        self.tensions: Tuple[Finding, ...] = tuple(tensions)
        self.gaps: Tuple[Finding, ...] = tuple(gaps)
        self.arguments: Dict[str, str] = dict(arguments or {})

    @property
    def relations(self) -> List[Relation]:
        """The derived edges only (asserted input is not copied)."""
        return [d.relation for d in self.derived]

    def by_rule(self) -> Dict[str, List[Derivation]]:
        grouped: Dict[str, List[Derivation]] = {}
        for d in self.derived:
            grouped.setdefault(d.rule, []).append(d)
        return grouped

    def summary(self) -> str:
        lines = [
            f"Analysis: {len(self.derived)} derived, "
            f"{len(self.tensions)} tension(s), {len(self.gaps)} gap(s)"
        ]
        by_rule = self.by_rule()
        if by_rule:
            parts = [f"{len(items)} {rule}" for rule, items in by_rule.items()]
            lines.append("  derived: " + ", ".join(parts))
        for finding in self.tensions:
            lines.append(f"  tension [{finding.kind}]: {finding.detail}")
        if self.gaps:
            counts: Dict[str, int] = {}
            for finding in self.gaps:
                counts[finding.kind] = counts.get(finding.kind, 0) + 1
            lines.append(
                "  gaps: " + ", ".join(f"{n} {kind}" for kind, n in counts.items())
            )
            preview = self.gaps[:8]
            for finding in preview:
                lines.append(f"    [{finding.kind}] {finding.detail}")
            extra = len(self.gaps) - len(preview)
            if extra:
                lines.append(f"    ... {extra} more")
        if self.arguments:
            buckets: Dict[str, List[str]] = {"accepted": [], "defeated": [], "undecided": []}
            for handle, status in self.arguments.items():
                buckets.setdefault(status, []).append(handle)
            bits = [f"{status}={', '.join(sorted(names))}" for status, names in buckets.items() if names]
            if bits:
                lines.append("  arguments: " + "; ".join(bits))
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "derived": [d.to_dict() for d in self.derived],
            "tensions": [f.to_dict() for f in self.tensions],
            "gaps": [f.to_dict() for f in self.gaps],
            "arguments": dict(self.arguments),
        }

    def __repr__(self) -> str:
        return (
            f"Analysis(derived={len(self.derived)}, tensions={len(self.tensions)}, "
            f"gaps={len(self.gaps)}, arguments={len(self.arguments)})"
        )


def analyze(
    values: Iterable[Union[Value, Dict[str, Any]]],
    *,
    transitive: PredicateSpec = None,
    symmetric: PredicateSpec = None,
    inherit_instantiation: bool = True,
    tensions: bool = True,
    gaps: bool = True,
    dung: bool = True,
) -> Analysis:
    """Run inference + tension detection over ``values``.

    ``values`` may be :class:`~valuez.values.Value` objects or stored document
    dicts. Derived edges are returned, not inserted. ``transitive`` and
    ``symmetric`` default to :data:`TRANSITIVE_PREDICATES` and
    :data:`SYMMETRIC_PREDICATES`.
    """
    hydrated = _hydrate(values)
    trans = _as_tuple(transitive, TRANSITIVE_PREDICATES)
    sym = _as_tuple(symmetric, SYMMETRIC_PREDICATES)

    concepts = [v for v in hydrated if isinstance(v, Concept)]
    relations = [v for v in hydrated if isinstance(v, Relation)]
    propositions = [v for v in hydrated if isinstance(v, Proposition)]
    arguments = [v for v in hydrated if isinstance(v, Argument)]

    derived = _infer(relations, trans, sym, inherit_instantiation)
    all_edges = list(relations) + [d.relation for d in derived]

    tension_findings: List[Finding] = []
    gap_findings: List[Finding] = []
    if tensions:
        tension_findings.extend(_find_cycles(relations, trans))
        tension_findings.extend(_find_clashes(all_edges))
        tension_findings.extend(_find_truth_clashes(propositions))
    if gaps:
        gap_findings.extend(_find_gaps(concepts, relations, propositions, arguments))

    statuses: Dict[str, str] = {}
    if dung:
        statuses = _dung_grounded(arguments, relations)

    return Analysis(
        derived=derived,
        tensions=tension_findings,
        gaps=gap_findings,
        arguments=statuses,
    )


def _infer(
    relations: Sequence[Relation],
    trans: Sequence[str],
    sym: Sequence[str],
    inherit_instantiation: bool,
) -> List[Derivation]:
    explicit: Set[Tuple[str, str, str]] = {_edge_key(r) for r in relations}
    derived: List[Derivation] = []

    def emit(rule: str, relation: Relation, because: Sequence[str]) -> None:
        key = _edge_key(relation)
        if key in explicit:
            return
        explicit.add(key)
        derived.append(Derivation(rule, relation, because))

    for predicate in trans:
        for source, target in sorted(reasoning.transitive_closure(relations, predicate)):
            if source == target:
                continue
            because = _path_because(relations, predicate, source, target)
            emit(
                "transitivity",
                Relation(
                    source,
                    predicate,
                    target,
                    modality="inferred",
                    id=f"inferred:transitivity:{predicate}:{source}:{target}",
                    reference=_derived_ref(
                        "transitivity",
                        f"inferred by transitivity of {predicate}",
                        because,
                    ),
                ),
                because,
            )

    for predicate in sym:
        for rel in relations:
            if rel.predicate != predicate or rel.source == rel.target:
                continue
            because = (rel.id,)
            emit(
                "symmetry",
                Relation(
                    rel.target,
                    predicate,
                    rel.source,
                    modality="inferred",
                    id=f"inferred:symmetry:{predicate}:{rel.target}:{rel.source}",
                    reference=_derived_ref(
                        "symmetry",
                        f"inferred by symmetry of {predicate}",
                        because,
                    ),
                ),
                because,
            )

    if inherit_instantiation:
        isa_pairs = reasoning.transitive_closure(relations, "is-a")
        instantiations = [r for r in relations if r.predicate == "instantiates"]
        for inst in instantiations:
            for kind, ancestor in sorted(isa_pairs):
                if inst.target != kind or ancestor == kind:
                    continue
                because = (inst.id,) + tuple(_path_because(relations, "is-a", kind, ancestor))
                emit(
                    "instantiation-inheritance",
                    Instantiation(
                        inst.source,
                        ancestor,
                        modality="inferred",
                        id=f"inferred:instantiates:{inst.source}:{ancestor}",
                        reference=_derived_ref(
                            "instantiation-inheritance",
                            f"{inst.source} instantiates {kind}, which is-a {ancestor}",
                            because,
                        ),
                    ),
                    because,
                )

    return derived


def _find_cycles(relations: Sequence[Relation], trans: Sequence[str]) -> List[Finding]:
    findings: List[Finding] = []
    for predicate in trans:
        for cycle in reasoning.find_cycles(relations, predicate):
            if not cycle:
                continue
            walk = " → ".join(list(cycle) + [cycle[0]])
            findings.append(
                Finding(
                    "cycle",
                    f"{predicate} cycle: {walk}",
                    items=list(cycle),
                )
            )
    return findings


def _undirected_index(relations: Sequence[Relation]) -> Dict[Tuple[str, str, str], List[Relation]]:
    """(node_lo, node_hi, predicate) -> relations between those two nodes with that predicate."""
    index: Dict[Tuple[str, str, str], List[Relation]] = {}
    for rel in relations:
        a, b = (rel.source, rel.target) if rel.source <= rel.target else (rel.target, rel.source)
        index.setdefault((a, b, rel.predicate), []).append(rel)
    return index


def _find_clashes(relations: Sequence[Relation]) -> List[Finding]:
    index = _undirected_index(relations)
    findings: List[Finding] = []
    seen: Set[Tuple[str, str, str, str]] = set()
    for left, right in _CLASH_PAIRS:
        for (a, b, pred), rels in index.items():
            if pred != left:
                continue
            others = index.get((a, b, right), [])
            if not others:
                continue
            key = (a, b, left, right)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    "clash",
                    f"{a} and {b} are related by both {left} and {right}",
                    items=[r.id for r in rels + others],
                )
            )
    return findings


def _find_truth_clashes(propositions: Sequence[Proposition]) -> List[Finding]:
    findings: List[Finding] = []
    groups: Dict[str, List[Proposition]] = {}
    for prop in propositions:
        groups.setdefault(f"statement:{prop.statement}", []).append(prop)
        groups.setdefault(f"handle:{prop.handle}", []).append(prop)
    seen_ids: Set[Tuple[str, ...]] = set()
    for key, group in groups.items():
        truths = {p.truth_value for p in group if p.truth_value is not None}
        if True in truths and False in truths:
            ids = tuple(sorted({p.id for p in group}))
            if ids in seen_ids:
                continue
            seen_ids.add(ids)
            label = key.split(":", 1)[1]
            findings.append(
                Finding(
                    "contradiction",
                    f"conflicting truth-values for {label!r}",
                    items=list(ids),
                )
            )
    return findings


def _find_gaps(
    concepts: Sequence[Concept],
    relations: Sequence[Relation],
    propositions: Sequence[Proposition],
    arguments: Sequence[Argument],
) -> List[Finding]:
    findings: List[Finding] = []
    named = {c.name for c in concepts}
    named |= {p.handle for p in propositions}
    named |= {a.handle for a in arguments}
    endpoints: Set[str] = set()
    cited_nodes: Set[str] = set()
    for rel in relations:
        endpoints.add(rel.source)
        endpoints.add(rel.target)
        if rel.reference is not None:
            cited_nodes.add(rel.source)
            cited_nodes.add(rel.target)
        if named:
            for end in (rel.source, rel.target):
                if end not in named:
                    findings.append(
                        Finding(
                            "dangling",
                            f"edge {rel.id} points at unknown node {end!r}",
                            items=(rel.id, end),
                        )
                    )

    for concept in concepts:
        if concept.name not in endpoints:
            findings.append(
                Finding("isolated", f"{concept.name} has no incident relations", items=(concept.name,))
            )
        if not concept.definition:
            findings.append(
                Finding("undefined", f"{concept.name} has no definition", items=(concept.name,))
            )
        if concept.reference is None and concept.name not in cited_nodes:
            findings.append(
                Finding("ungrounded", f"{concept.name} carries no Reference", items=(concept.name,))
            )

    for prop in propositions:
        if prop.truth_value is None:
            findings.append(
                Finding(
                    "open-question",
                    f"proposition {prop.handle!r} has no truth-value",
                    items=(prop.id,),
                )
            )

    handles = {p.handle for p in propositions}
    for arg in arguments:
        missing = [h for h in list(arg.premises) + [arg.conclusion] if h not in handles]
        if missing:
            findings.append(
                Finding(
                    "missing-premise",
                    f"argument {arg.handle!r} refers to unknown claim(s): {', '.join(missing)}",
                    items=tuple(missing),
                )
            )

    return findings


def _dung_grounded(arguments: Sequence[Argument], relations: Sequence[Relation]) -> Dict[str, str]:
    """Grounded semantics over argument-vs-argument ``attacks`` edges."""
    handles = [a.handle for a in arguments]
    if not handles:
        return {}
    known = set(handles)
    attackers: Dict[str, List[str]] = {h: [] for h in handles}
    for rel in relations:
        if rel.predicate != "attacks":
            continue
        if rel.source in known and rel.target in known:
            attackers[rel.target].append(rel.source)

    in_set: Set[str] = set()
    while True:
        out_set = {h for h in handles if any(att in in_set for att in attackers[h])}
        new_in = {h for h in handles if all(att in out_set for att in attackers[h])}
        if new_in == in_set:
            break
        in_set = new_in

    out_set = {h for h in handles if any(att in in_set for att in attackers[h])}
    statuses: Dict[str, str] = {}
    for h in handles:
        if h in in_set:
            statuses[h] = "accepted"
        elif h in out_set:
            statuses[h] = "defeated"
        else:
            statuses[h] = "undecided"
    return statuses
