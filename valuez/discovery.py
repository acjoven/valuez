"""Cross-universe discovery: unexpected paths created by joining ontologies.

Merging two maps by name stitches them at join points (``Freedom``, ``God``,
...). That seam is visible in the merge report. This module asks the next
question: **which concepts that lived in only one source are now close to
concepts that lived only in the other?**

Those paths do not exist in either ontology alone -- they are an artifact of
the join -- so they are the first kind of *unexpected connection* the active-
knowledge track wants. Thematic clustering and proposing new bridging concepts
are later slices.

A crossing is a shortest undirected path from an *exclusive* node of source A
to an exclusive node of source B that passes through at least one join point.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .merge import MergeResult, merge_ontologies
from .traversal import Path as Walk

__all__ = ["Crossing", "Discovery", "discover"]


class Crossing:
    """One exclusive-to-exclusive path that exists only in the merged universe."""

    def __init__(
        self,
        path: Walk,
        *,
        from_source: str,
        to_source: str,
        via: Sequence[str],
    ) -> None:
        self.path = path
        self.from_source = from_source
        self.to_source = to_source
        self.via: Tuple[str, ...] = tuple(via)

    @property
    def start(self) -> str:
        return self.path.start

    @property
    def end(self) -> str:
        return self.path.end

    @property
    def hops(self) -> int:
        return self.path.length

    def describe(self) -> str:
        joins = ", ".join(self.via) if self.via else "?"
        return (
            f"{self.start} [{self.from_source}] ~ {joins} ~ "
            f"{self.end} [{self.to_source}]  ({self.hops} hop(s))\n"
            f"  {self.path.describe()}"
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "from_source": self.from_source,
            "to_source": self.to_source,
            "via": list(self.via),
            "hops": self.hops,
            "path": self.path.describe(),
        }

    def __repr__(self) -> str:
        return (
            f"Crossing({self.start!r} [{self.from_source}] ~ {self.end!r} "
            f"[{self.to_source}], hops={self.hops})"
        )


class Discovery:
    """The crossings that a merge created, ranked shortest-first."""

    def __init__(
        self,
        *,
        sources: Sequence[str],
        exclusive: Dict[str, Sequence[str]],
        join_points: Sequence[str],
        crossings: Sequence[Crossing],
        total: int,
        hubs: Sequence[Tuple[str, int]],
    ) -> None:
        self.sources: Tuple[str, ...] = tuple(sources)
        self.exclusive: Dict[str, Tuple[str, ...]] = {
            src: tuple(names) for src, names in exclusive.items()
        }
        self.join_points: Tuple[str, ...] = tuple(join_points)
        self.crossings: Tuple[Crossing, ...] = tuple(crossings)
        self.total = total
        self.hubs: Tuple[Tuple[str, int], ...] = tuple(hubs)

    def between(self, from_source: str, to_source: str) -> Tuple[Crossing, ...]:
        """Crossings that run from ``from_source`` exclusive nodes to ``to_source``."""
        return tuple(
            c
            for c in self.crossings
            if c.from_source == from_source and c.to_source == to_source
        )

    def via(self, join: str) -> Tuple[Crossing, ...]:
        """Crossings (in the ranked list) that pass through this join point."""
        return tuple(c for c in self.crossings if join in c.via)

    def summary(self) -> str:
        lines = [
            f"Discovery: {self.total} crossing(s) across {len(self.sources)} sources "
            f"(showing {len(self.crossings)})"
        ]
        for src, names in self.exclusive.items():
            lines.append(f"  exclusive to {src}: {len(names)} node(s)")
        lines.append(f"  join points: {', '.join(self.join_points) or '(none)'}")
        if self.hubs:
            top = ", ".join(f"{name} ({n})" for name, n in self.hubs[:8])
            lines.append(f"  hubs (join points carrying the most crossings): {top}")
        for crossing in self.crossings[:12]:
            lines.append("  " + crossing.describe().replace("\n", "\n  "))
        extra = len(self.crossings) - min(12, len(self.crossings))
        if extra:
            lines.append(f"  ... {extra} more")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": list(self.sources),
            "exclusive": {s: list(n) for s, n in self.exclusive.items()},
            "join_points": list(self.join_points),
            "total": self.total,
            "hubs": [{"join": name, "crossings": n} for name, n in self.hubs],
            "crossings": [c.to_dict() for c in self.crossings],
        }

    def __repr__(self) -> str:
        return (
            f"Discovery(sources={self.sources!r}, crossings={len(self.crossings)}/"
            f"{self.total})"
        )


def discover(
    universe: Union[MergeResult, Sequence[Any]],
    *,
    cutoff: int = 3,
    limit: int = 40,
    directed: bool = False,
) -> Discovery:
    """Find exclusive-to-exclusive paths created by joining ontologies.

    ``universe`` is a :class:`~valuez.merge.MergeResult` or anything
    :func:`~valuez.merge.merge_ontologies` accepts (a list of files / repos /
    value iterables). Paths are undirected by default, capped at ``cutoff`` hops,
    ranked shortest-first, then truncated to ``limit`` (``limit=0`` keeps all).
    """
    if not isinstance(universe, MergeResult):
        universe = merge_ontologies(universe)
    if not isinstance(cutoff, int) or isinstance(cutoff, bool) or cutoff < 1:
        raise ValueError("cutoff must be a positive integer")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
        raise ValueError("limit must be a non-negative integer")

    report = universe.report
    if not report.node_sources:
        raise ValueError(
            "merge report has no node_sources; re-merge with the current "
            "valuez.merge to record per-node provenance"
        )

    joins = set(report.join_points)
    exclusive: Dict[str, List[str]] = {src: [] for src in report.sources}
    for name, labels in report.node_sources.items():
        if len(labels) == 1:
            exclusive[labels[0]].append(name)
    for src in exclusive:
        exclusive[src].sort()

    graph = universe.graph()
    collected: List[Crossing] = []
    sources = list(report.sources)
    for i, src_a in enumerate(sources):
        for src_b in sources[i + 1 :]:
            collected.extend(
                _crossings(
                    graph,
                    exclusive[src_a],
                    exclusive[src_b],
                    src_a,
                    src_b,
                    joins,
                    cutoff,
                    directed,
                )
            )
            collected.extend(
                _crossings(
                    graph,
                    exclusive[src_b],
                    exclusive[src_a],
                    src_b,
                    src_a,
                    joins,
                    cutoff,
                    directed,
                )
            )

    collected.sort(key=lambda c: (c.hops, c.start, c.end, c.from_source, c.to_source))
    total = len(collected)
    hub_counts: Dict[str, int] = {j: 0 for j in joins}
    for crossing in collected:
        for join in set(crossing.via):
            hub_counts[join] = hub_counts.get(join, 0) + 1
    hubs = tuple(sorted(hub_counts.items(), key=lambda kv: (-kv[1], kv[0])))
    if limit:
        collected = collected[:limit]

    return Discovery(
        sources=report.sources,
        exclusive=exclusive,
        join_points=sorted(joins),
        crossings=collected,
        total=total,
        hubs=hubs,
    )


def _crossings(
    graph: Any,
    starts: Sequence[str],
    ends: Sequence[str],
    from_source: str,
    to_source: str,
    joins: set,
    cutoff: int,
    directed: bool,
) -> List[Crossing]:
    end_set = set(ends)
    if not starts or not end_set:
        return []
    found: List[Crossing] = []
    for start in starts:
        if start not in graph:
            continue
        paths = graph.shortest_paths_from(start, cutoff=cutoff, directed=directed)
        for end, path in paths.items():
            if end not in end_set or path.length < 2:
                continue
            via = tuple(n for n in path.nodes[1:-1] if n in joins)
            if not via:
                continue
            found.append(
                Crossing(path, from_source=from_source, to_source=to_source, via=via)
            )
    return found
