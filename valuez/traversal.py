"""Graph traversal and path queries over valuez relation graphs.

The rest of the *active knowledge* track (concept briefs, path-based discovery,
guided reading) leans on being able to ask, of a stored ontology:

- what sits next to this node? (:meth:`Graph.neighborhood`)
- how does A relate to B? (:meth:`Graph.how` / :meth:`Graph.paths`)
- what is the topic subgraph around these seeds? (:meth:`Graph.topic`)

This module is *mechanics*: it does not invent nodes or edges. Every hop on a
returned :class:`Path` is an asserted :class:`~valuez.semantic.Relation` (or
:class:`~valuez.metaphysics.Instantiation`), so provenance rides along.

Nodes are keyed by **name**, matching how :class:`~valuez.semantic.Relation`
stores its endpoints. Isolated named nodes (a ``Concept`` / ``Individual`` /
``Universal`` with no incident edge) are still addressable when the graph is
built from values, not only from edges.

``networkx`` is imported lazily, the same way :mod:`valuez.reasoning` does.
"""
from __future__ import annotations

import json
from pathlib import Path as FsPath
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from .semantic import Concept, Relation
from .values import Value

__all__ = [
    "Hop",
    "Path",
    "Neighborhood",
    "Graph",
    "neighborhood",
    "shortest_path",
    "paths",
    "how",
    "topic",
]

ConceptRef = Union[str, Concept]
PredicateSpec = Optional[Union[str, Iterable[str]]]
Direction = str  # "out" | "in" | "both"

_DIRECTIONS = ("out", "in", "both")


def _node_name(value: ConceptRef, field: str = "node") -> str:
    if isinstance(value, Concept):
        return value.name
    if isinstance(value, str) and value:
        return value
    raise ValueError(f"{field} must be a non-empty string or Concept")


def _predicate_set(predicates: PredicateSpec) -> Optional[Set[str]]:
    if predicates is None:
        return None
    if isinstance(predicates, str):
        if not predicates:
            raise ValueError("predicates must be a non-empty string or an iterable of strings")
        return {predicates}
    out = {p for p in predicates}
    if not out or any(not isinstance(p, str) or not p for p in out):
        raise ValueError("predicates must be a non-empty string or an iterable of strings")
    return out


def _matches(relation: Relation, predicates: Optional[Set[str]]) -> bool:
    return predicates is None or relation.predicate in predicates


def _check_direction(direction: str) -> str:
    if direction not in _DIRECTIONS:
        raise ValueError(f"direction must be one of {_DIRECTIONS}, got {direction!r}")
    return direction


def _relation_sort_key(relation: Relation) -> Tuple[str, str, str, str]:
    return (relation.source, relation.predicate, relation.target, relation.id)


class Hop:
    """One step of a walk: the relation(s) connecting two consecutive nodes.

    ``source`` / ``target`` are the walk direction (which may run *against* an
    asserted edge when the search is undirected). Parallel edges between the
    same pair (different predicates) are kept together so nothing is dropped.
    """

    def __init__(self, source: str, target: str, relations: Sequence[Relation]) -> None:
        if not relations:
            raise ValueError("Hop requires at least one Relation")
        self.source = source
        self.target = target
        self.relations: Tuple[Relation, ...] = tuple(sorted(relations, key=_relation_sort_key))

    @property
    def forward(self) -> bool:
        """True when at least one stored edge runs ``source -> target``."""
        return any(r.source == self.source and r.target == self.target for r in self.relations)

    @property
    def predicates(self) -> Tuple[str, ...]:
        return tuple(sorted({r.predicate for r in self.relations}))

    def describe(self) -> str:
        preds = "|".join(self.predicates)
        if self.forward:
            return f"{self.source} -{preds}-> {self.target}"
        return f"{self.source} <-{preds}- {self.target}"

    def __repr__(self) -> str:
        return f"Hop({self.describe()})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Hop):
            return NotImplemented
        return (
            self.source == other.source
            and self.target == other.target
            and self.relations == other.relations
        )


class Path:
    """A walk through the graph: nodes interleaved with the :class:`Hop`s that connect them."""

    def __init__(self, nodes: Sequence[str], hops: Sequence[Hop] = ()) -> None:
        self.nodes: Tuple[str, ...] = tuple(nodes)
        self.hops: Tuple[Hop, ...] = tuple(hops)
        if self.hops and len(self.nodes) != len(self.hops) + 1:
            raise ValueError("Path must have one more node than hops")
        if not self.nodes:
            raise ValueError("Path requires at least one node")

    @property
    def start(self) -> str:
        return self.nodes[0]

    @property
    def end(self) -> str:
        return self.nodes[-1]

    @property
    def length(self) -> int:
        """Number of hops (0 for a single-node path)."""
        return len(self.hops)

    @property
    def relations(self) -> Tuple[Relation, ...]:
        """Flattened relations along the walk (parallel edges included)."""
        out: List[Relation] = []
        for hop in self.hops:
            out.extend(hop.relations)
        return tuple(out)

    def describe(self) -> str:
        """Human-readable 'how A relates to B' rendering.

        Example::

            Space -is-form-of-> Intuition -is-a-> Representation <-is-a- Concept
        """
        if not self.hops:
            return self.nodes[0]
        parts: List[str] = [self.hops[0].source]
        for hop in self.hops:
            preds = "|".join(hop.predicates)
            parts.append(f"-{preds}->" if hop.forward else f"<-{preds}-")
            parts.append(hop.target)
        return " ".join(parts)

    def __str__(self) -> str:
        return self.describe()

    def __repr__(self) -> str:
        return f"Path({self.describe()!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Path):
            return NotImplemented
        return self.nodes == other.nodes and self.hops == other.hops

    def __len__(self) -> int:
        return self.length


class Neighborhood:
    """The k-hop vicinity of a node, plus the induced edges among those nodes."""

    def __init__(
        self,
        center: str,
        hops: int,
        nodes: Iterable[str],
        relations: Sequence[Relation],
    ) -> None:
        self.center = center
        self.hops = hops
        self.nodes: Tuple[str, ...] = tuple(sorted(set(nodes)))
        self.relations: Tuple[Relation, ...] = tuple(sorted(relations, key=_relation_sort_key))

    def graph(self) -> "Graph":
        """This neighborhood as a :class:`Graph` (a topic subgraph)."""
        return Graph.from_relations(self.relations, nodes=self.nodes)

    def __contains__(self, name: object) -> bool:
        return name in self.nodes

    def __len__(self) -> int:
        return len(self.nodes)

    def __repr__(self) -> str:
        return (
            f"Neighborhood(center={self.center!r}, hops={self.hops}, "
            f"nodes={len(self.nodes)}, edges={len(self.relations)})"
        )


class Graph:
    """A directed relation graph with neighborhood, path, and topic queries.

    Build from edges, from mixed values (nodes + edges), from a stored ontology,
    or from a :class:`~valuez.reading.Reading` / :class:`~valuez.repository.ValueRepository`.
    """

    def __init__(
        self,
        relations: Iterable[Relation] = (),
        *,
        nodes: Optional[Iterable[str]] = None,
    ) -> None:
        rels = [r for r in relations]
        for r in rels:
            if not isinstance(r, Relation):
                raise TypeError(f"expected Relation, got {type(r).__name__}")
        self._relations: Tuple[Relation, ...] = tuple(sorted(rels, key=_relation_sort_key))
        names: Set[str] = set(nodes or ())
        for r in self._relations:
            names.add(r.source)
            names.add(r.target)
        self._nodes: Set[str] = names

    # ------------------------------------------------------------------ #
    # Constructors                                                        #
    # ------------------------------------------------------------------ #
    @classmethod
    def from_relations(
        cls,
        relations: Iterable[Relation],
        *,
        nodes: Optional[Iterable[str]] = None,
    ) -> "Graph":
        return cls(relations, nodes=nodes)

    @classmethod
    def from_values(cls, values: Iterable[Union[Value, Dict[str, Any]]]) -> "Graph":
        """Build from mixed values (or document dicts). Named nodes are kept even if isolated."""
        rels: List[Relation] = []
        names: List[str] = []
        for item in values:
            value = item if isinstance(item, Value) else Value.from_dict(item)
            if isinstance(value, Relation):
                rels.append(value)
            elif isinstance(value, Concept):
                names.append(value.name)
        return cls(rels, nodes=names)

    @classmethod
    def from_documents(cls, docs: Iterable[Dict[str, Any]]) -> "Graph":
        return cls.from_values(docs)

    @classmethod
    def from_ontology(cls, path: Union[str, FsPath]) -> "Graph":
        """Load a canonical ``ontologies/*.json`` array without spinning up a store."""
        data = json.loads(FsPath(path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected a JSON array of documents")
        return cls.from_documents(data)

    @classmethod
    def from_reading(cls, reading: Any) -> "Graph":
        return cls.from_values(reading.values())

    @classmethod
    def from_repository(cls, repo: Any) -> "Graph":
        return cls.from_documents(repo.query("[]"))

    # ------------------------------------------------------------------ #
    # Access                                                              #
    # ------------------------------------------------------------------ #
    @property
    def relations(self) -> Tuple[Relation, ...]:
        return self._relations

    @property
    def nodes(self) -> Tuple[str, ...]:
        return tuple(sorted(self._nodes))

    @property
    def n_nodes(self) -> int:
        return len(self._nodes)

    @property
    def n_edges(self) -> int:
        return len(self._relations)

    def __contains__(self, name: object) -> bool:
        return name in self._nodes

    def __len__(self) -> int:
        return self.n_nodes

    def __repr__(self) -> str:
        return f"Graph(nodes={self.n_nodes}, edges={self.n_edges})"

    def has_node(self, name: ConceptRef) -> bool:
        return _node_name(name) in self._nodes

    def _require(self, name: ConceptRef, field: str = "node") -> str:
        key = _node_name(name, field)
        if key not in self._nodes:
            raise ValueError(f"unknown node {key!r}")
        return key

    def incident(
        self,
        node: ConceptRef,
        *,
        predicates: PredicateSpec = None,
        direction: Direction = "both",
    ) -> List[Relation]:
        """Relations touching ``node``, optionally filtered by predicate / direction."""
        name = self._require(node)
        predset = _predicate_set(predicates)
        direction = _check_direction(direction)
        out: List[Relation] = []
        for rel in self._relations:
            if not _matches(rel, predset):
                continue
            if direction in ("out", "both") and rel.source == name:
                out.append(rel)
            elif direction in ("in", "both") and rel.target == name:
                out.append(rel)
        return out

    def neighbors(
        self,
        node: ConceptRef,
        *,
        predicates: PredicateSpec = None,
        direction: Direction = "both",
    ) -> List[str]:
        """Adjacent node names (sorted, de-duplicated)."""
        name = self._require(node)
        names: Set[str] = set()
        for rel in self.incident(node, predicates=predicates, direction=direction):
            other = rel.target if rel.source == name else rel.source
            names.add(other)
        return sorted(names)

    # ------------------------------------------------------------------ #
    # Neighborhood / topic                                                #
    # ------------------------------------------------------------------ #
    def neighborhood(
        self,
        node: ConceptRef,
        hops: int = 1,
        *,
        predicates: PredicateSpec = None,
        direction: Direction = "both",
    ) -> Neighborhood:
        """k-hop vicinity of ``node``, with the induced edges among those nodes.

        ``hops=0`` is just the center. Discovery follows ``direction``; the
        returned edges are every matching relation whose *both* endpoints landed
        in the vicinity (so a topic subgraph is internally complete).
        """
        if not isinstance(hops, int) or isinstance(hops, bool) or hops < 0:
            raise ValueError("hops must be a non-negative integer")
        center = self._require(node)
        predset = _predicate_set(predicates)
        direction = _check_direction(direction)

        seen: Set[str] = {center}
        frontier: Set[str] = {center}
        for _ in range(hops):
            nxt: Set[str] = set()
            for current in frontier:
                for rel in self._relations:
                    if not _matches(rel, predset):
                        continue
                    other: Optional[str] = None
                    if direction in ("out", "both") and rel.source == current:
                        other = rel.target
                    elif direction in ("in", "both") and rel.target == current:
                        other = rel.source
                    if other is not None and other not in seen:
                        nxt.add(other)
                        seen.add(other)
            frontier = nxt
            if not frontier:
                break

        induced = [
            rel
            for rel in self._relations
            if _matches(rel, predset) and rel.source in seen and rel.target in seen
        ]
        return Neighborhood(center, hops, seen, induced)

    def subgraph(self, nodes: Iterable[ConceptRef]) -> "Graph":
        """Induced subgraph on ``nodes`` (unknown names raise)."""
        keep = {self._require(n) for n in nodes}
        rels = [r for r in self._relations if r.source in keep and r.target in keep]
        return Graph.from_relations(rels, nodes=keep)

    def topic(
        self,
        seed: Union[ConceptRef, Iterable[ConceptRef]],
        hops: int = 1,
        *,
        predicates: PredicateSpec = None,
        direction: Direction = "both",
    ) -> "Graph":
        """Induced subgraph of the k-hop neighborhood of one or more seeds."""
        if isinstance(seed, (str, Concept)):
            seeds: List[ConceptRef] = [seed]
        else:
            seeds = list(seed)
            if not seeds:
                raise ValueError("topic() requires at least one seed")
        names: Set[str] = set()
        for s in seeds:
            names.update(self.neighborhood(s, hops, predicates=predicates, direction=direction).nodes)
        return self.subgraph(names)

    # ------------------------------------------------------------------ #
    # Paths / "how does A relate to B"                                    #
    # ------------------------------------------------------------------ #
    def shortest_path(
        self,
        source: ConceptRef,
        target: ConceptRef,
        *,
        directed: bool = True,
        predicates: PredicateSpec = None,
    ) -> Optional[Path]:
        """A shortest path, or ``None`` if the nodes are disconnected.

        Directed by default (follows asserted edge direction). Isolated
        ``source == target`` is a zero-hop path.
        """
        src = self._require(source, "source")
        tgt = self._require(target, "target")
        predset = _predicate_set(predicates)
        if src == tgt:
            return Path([src])

        import networkx as nx

        graph = self._nx_view(directed=directed, predicates=predset)
        try:
            node_path = nx.shortest_path(graph, src, tgt)
        except nx.NetworkXNoPath:
            return None
        return self._rehydrate_path(node_path, predset)

    def shortest_paths_from(
        self,
        source: ConceptRef,
        *,
        cutoff: Optional[int] = None,
        directed: bool = False,
        predicates: PredicateSpec = None,
    ) -> Dict[str, Path]:
        """Shortest path from ``source`` to every reachable node.

        Undirected by default (same as :meth:`how`). ``cutoff`` caps hop count.
        The source itself is omitted. Used by cross-universe discovery to batch
        BFS instead of running one :meth:`shortest_path` per pair.
        """
        if cutoff is not None and (not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 0):
            raise ValueError("cutoff must be a non-negative integer or None")
        src = self._require(source, "source")
        predset = _predicate_set(predicates)
        import networkx as nx

        graph = self._nx_view(directed=directed, predicates=predset)
        kwargs: Dict[str, Any] = {}
        if cutoff is not None:
            kwargs["cutoff"] = cutoff
        raw = nx.single_source_shortest_path(graph, src, **kwargs)
        return {
            target: self._rehydrate_path(nodes, predset)
            for target, nodes in raw.items()
            if target != src
        }

    def how(
        self,
        source: ConceptRef,
        target: ConceptRef,
        *,
        directed: bool = False,
        predicates: PredicateSpec = None,
    ) -> Optional[Path]:
        """How does ``source`` relate to ``target``?

        Undirected by default: the interesting question is whether a chain of
        asserted edges connects the two names, not whether you already know the
        arrow direction. Returns ``None`` when there is no connecting path.
        """
        return self.shortest_path(source, target, directed=directed, predicates=predicates)

    def paths(
        self,
        source: ConceptRef,
        target: ConceptRef,
        *,
        cutoff: Optional[int] = 6,
        limit: int = 20,
        directed: bool = False,
        predicates: PredicateSpec = None,
    ) -> List[Path]:
        """Simple paths from ``source`` to ``target``.

        Undirected by default. ``cutoff`` caps hop count (``None`` = unbounded);
        ``limit`` caps how many paths are returned (shortest first, then
        lexicographic node sequence). ``limit=0`` means no cap.
        """
        if cutoff is not None and (not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 0):
            raise ValueError("cutoff must be a non-negative integer or None")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        src = self._require(source, "source")
        tgt = self._require(target, "target")
        predset = _predicate_set(predicates)

        if src == tgt:
            return [Path([src])]

        import networkx as nx

        graph = self._nx_view(directed=directed, predicates=predset)
        if src not in graph or tgt not in graph:
            return []
        kwargs: Dict[str, Any] = {}
        if cutoff is not None:
            kwargs["cutoff"] = cutoff
        collected = [tuple(p) for p in nx.all_simple_paths(graph, src, tgt, **kwargs)]
        collected.sort(key=lambda p: (len(p), p))
        if limit:
            collected = collected[:limit]
        return [self._rehydrate_path(nodes, predset) for nodes in collected]

    def _nx_view(self, *, directed: bool, predicates: Optional[Set[str]]) -> Any:
        import networkx as nx

        graph = nx.DiGraph() if directed else nx.Graph()
        graph.add_nodes_from(self._nodes)
        for rel in self._relations:
            if _matches(rel, predicates):
                graph.add_edge(rel.source, rel.target)
        return graph

    def _hops_between(self, a: str, b: str, predicates: Optional[Set[str]]) -> Hop:
        forward = [
            rel
            for rel in self._relations
            if _matches(rel, predicates) and rel.source == a and rel.target == b
        ]
        if forward:
            return Hop(a, b, forward)
        reverse = [
            rel
            for rel in self._relations
            if _matches(rel, predicates) and rel.source == b and rel.target == a
        ]
        if reverse:
            return Hop(a, b, reverse)
        raise ValueError(f"no edge between {a!r} and {b!r}")

    def _rehydrate_path(self, nodes: Sequence[str], predicates: Optional[Set[str]]) -> Path:
        hops = [self._hops_between(nodes[i], nodes[i + 1], predicates) for i in range(len(nodes) - 1)]
        return Path(nodes, hops)

    # ------------------------------------------------------------------ #
    # Visualization                                                       #
    # ------------------------------------------------------------------ #
    def visualize(self, output_html: Union[str, FsPath]) -> FsPath:
        """Render this graph to interactive HTML via :func:`visualize_relations`."""
        from .semantic import visualize_relations

        return visualize_relations(self._relations, output_html)


# Module-level helpers matching :mod:`valuez.reasoning`'s functional style.


def neighborhood(
    relations: Iterable[Relation],
    node: ConceptRef,
    hops: int = 1,
    **kwargs: Any,
) -> Neighborhood:
    return Graph.from_relations(relations).neighborhood(node, hops, **kwargs)


def shortest_path(
    relations: Iterable[Relation],
    source: ConceptRef,
    target: ConceptRef,
    **kwargs: Any,
) -> Optional[Path]:
    return Graph.from_relations(relations).shortest_path(source, target, **kwargs)


def paths(
    relations: Iterable[Relation],
    source: ConceptRef,
    target: ConceptRef,
    **kwargs: Any,
) -> List[Path]:
    return Graph.from_relations(relations).paths(source, target, **kwargs)


def how(
    relations: Iterable[Relation],
    source: ConceptRef,
    target: ConceptRef,
    **kwargs: Any,
) -> Optional[Path]:
    return Graph.from_relations(relations).how(source, target, **kwargs)


def topic(
    relations: Iterable[Relation],
    seed: Union[ConceptRef, Iterable[ConceptRef]],
    hops: int = 1,
    **kwargs: Any,
) -> Graph:
    return Graph.from_relations(relations).topic(seed, hops, **kwargs)
