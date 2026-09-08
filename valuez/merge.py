"""Merge multiple valuez ontologies into one larger "universe".

Each ontology is a set of serialized :class:`~valuez.values.Value` documents
(as produced by :meth:`ValueRepository.export_ontology`). Two ontologies authored
independently -- e.g. ``ontologies/kant.json`` and ``ontologies/kierkegaard.json``
-- may describe some of the *same* concepts under the *same name* (``Freedom``,
``God``, ``Philosopher``, ...). Merging them should not just concatenate the two
files; it should **identify those points of overlap and join the common nodes**,
so the two graphs become one connected universe.

The join key is a node's **name**. This works because edges
(:class:`~valuez.Relation` / :class:`~valuez.Instantiation`) reference their
endpoints *by name*: once two same-named nodes collapse into one, every edge
from either source automatically attaches to that single node, wiring the two
subgraphs together through the shared concept -- no edge rewriting required.

What this module does:

- **Named nodes** (``concept`` / ``individual`` / ``universal``) are grouped by
  ``name``. A name seen in more than one source is a **join point**; its
  contributors are reconciled into one node (see ``on_conflict``), recording any
  genuine divergence (a different ``definition`` / ``ontological_status``, or --
  a *type* conflict -- a different ``kind``).
- **Edges** (``relation`` / ``instantiation``) are carried over and, by default,
  de-duplicated: an identical triple asserted by both sources collapses to one
  edge (its shared provenance is reported).
- **Everything else** (propositions, arguments, scalars, ...) is carried over,
  with a final pass guaranteeing globally unique ids.

The result is a :class:`MergeResult` -- the merged documents plus a
:class:`MergeReport` describing the join points, conflicts, and de-duplication --
which you can rehydrate to values, persist through ``dotz``, or export as a new
canonical ontology.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from .values import Value

__all__ = ["merge_ontologies", "MergeResult", "MergeReport"]

# Node kinds joined by ``name`` (the shared identity across ontologies).
NAME_NODE_KINDS = frozenset({"concept", "individual", "universal"})
# Edge kinds whose endpoints reference nodes by ``name``.
EDGE_KINDS = frozenset({"relation", "instantiation"})
# Node fields reconciled (beyond ``name``) when joining common nodes.
_MERGE_FIELDS = ("definition", "ontological_status", "label", "reference")

_CONFLICT_POLICIES = ("first", "last", "raise")

SourceSpec = Union[str, Path, Any, Iterable[Union[Value, Dict[str, Any]]]]


def _load_documents(source: SourceSpec, index: int) -> Tuple[str, List[Dict[str, Any]]]:
    """Normalize one source into ``(label, [document dicts])``."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        docs = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(docs, list):
            raise ValueError(f"{path}: expected a JSON array of documents")
        return path.stem, [dict(d) for d in docs]
    # A ValueRepository (or anything exposing ``query``) -> all its documents.
    query = getattr(source, "query", None)
    if callable(query):
        return f"source_{index}", [dict(d) for d in query("[]")]
    # An iterable of Value objects and/or plain dicts.
    docs = []
    for item in source:
        if isinstance(item, Value):
            docs.append(item.to_dict())
        elif isinstance(item, dict):
            docs.append(dict(item))
        else:
            raise TypeError(f"source_{index}: unsupported document {type(item).__name__}")
    return f"source_{index}", docs


def _edge_key(doc: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        doc.get("kind"),
        doc.get("source"),
        doc.get("predicate"),
        doc.get("target"),
        doc.get("modality"),
        doc.get("strength"),
    )


class MergeReport:
    """A human- and machine-readable account of what a merge did."""

    def __init__(self) -> None:
        self.sources: List[str] = []
        self.input_counts: Dict[str, int] = {}
        self.input_total: int = 0
        self.output_total: int = 0
        self.named_nodes_out: int = 0
        self.edges_in: int = 0
        self.edges_out: int = 0
        self.edges_deduped: int = 0
        # join points: name -> list of contributing source labels (len >= 2)
        self.join_points: Dict[str, List[str]] = {}
        # edges asserted identically by >1 source: edge triple -> labels
        self.shared_edges: List[Tuple[Tuple[Any, ...], List[str]]] = []
        # name -> {label: kind} where kinds disagree
        self.type_conflicts: Dict[str, Dict[str, str]] = {}
        # name -> field -> {label: value} where non-null values disagree
        self.field_conflicts: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.id_collisions: List[Tuple[str, str]] = []
        self.dangling_edges: List[Tuple[str, str]] = []

    @property
    def join_point_count(self) -> int:
        return len(self.join_points)

    def summary(self) -> str:
        lines: List[str] = []
        srcs = ", ".join(f"{s} ({self.input_counts.get(s, 0)})" for s in self.sources)
        lines.append(f"Merged {len(self.sources)} sources: {srcs}")
        lines.append(f"Documents: {self.input_total} in -> {self.output_total} out")
        lines.append(
            f"Join points (common nodes joined): {self.join_point_count}"
        )
        for name in sorted(self.join_points):
            flag = ""
            if name in self.type_conflicts:
                flag = "  [TYPE CONFLICT]"
            elif name in self.field_conflicts:
                flag = "  [differs: " + ", ".join(sorted(self.field_conflicts[name])) + "]"
            lines.append(f"    {name}  <- {', '.join(self.join_points[name])}{flag}")
        lines.append(
            f"Edges: {self.edges_in} in -> {self.edges_out} out "
            f"({self.edges_deduped} duplicate(s) collapsed, "
            f"{len(self.shared_edges)} asserted by multiple sources)"
        )
        if self.type_conflicts:
            lines.append(f"Type conflicts: {len(self.type_conflicts)}")
            for name, kinds in sorted(self.type_conflicts.items()):
                detail = ", ".join(f"{lbl}={k}" for lbl, k in kinds.items())
                lines.append(f"    {name}: {detail}")
        if self.field_conflicts:
            lines.append(f"Field conflicts (resolved by policy): {len(self.field_conflicts)}")
        if self.id_collisions:
            lines.append(f"Id collisions renamed: {len(self.id_collisions)}")
        if self.dangling_edges:
            lines.append(f"WARNING: dangling edge endpoints: {len(self.dangling_edges)}")
            for edge_id, endpoint in self.dangling_edges:
                lines.append(f"    {edge_id}: missing node {endpoint!r}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sources": list(self.sources),
            "input_counts": dict(self.input_counts),
            "input_total": self.input_total,
            "output_total": self.output_total,
            "named_nodes_out": self.named_nodes_out,
            "edges": {
                "in": self.edges_in,
                "out": self.edges_out,
                "deduped": self.edges_deduped,
                "shared": len(self.shared_edges),
            },
            "join_points": {k: list(v) for k, v in self.join_points.items()},
            "type_conflicts": {k: dict(v) for k, v in self.type_conflicts.items()},
            "field_conflicts": {
                k: {f: dict(vs) for f, vs in fields.items()}
                for k, fields in self.field_conflicts.items()
            },
            "id_collisions": [list(t) for t in self.id_collisions],
            "dangling_edges": [list(t) for t in self.dangling_edges],
        }


class MergeResult:
    """The merged universe: documents plus a :class:`MergeReport`."""

    def __init__(self, documents: List[Dict[str, Any]], report: MergeReport) -> None:
        self.documents = documents
        self.report = report

    def values(self) -> List[Value]:
        """Rehydrate the merged documents into :class:`Value` objects."""
        return [Value.from_dict(d) for d in self.documents]

    def relations(self) -> List[Value]:
        """The merged edges (relations + instantiations), rehydrated for rendering."""
        return [Value.from_dict(d) for d in self.documents if d.get("kind") in EDGE_KINDS]

    def named_nodes(self) -> List[Value]:
        """The merged named nodes (concepts / individuals / universals)."""
        return [Value.from_dict(d) for d in self.documents if d.get("kind") in NAME_NODE_KINDS]

    def graph(self) -> Any:
        """Relation graph over the merged universe, for neighborhood / path queries."""
        from .traversal import Graph

        return Graph.from_documents(self.documents)

    def analyze(self, **kwargs: Any) -> Any:
        """Inference + tension detection over the merged universe. See :func:`valuez.analyze`."""
        from .analysis import analyze

        return analyze(self.documents, **kwargs)

    def to_repository(self, data_dir: Optional[Union[str, Path]] = None) -> Any:
        """Persist the merged universe into a new :class:`ValueRepository`."""
        from .repository import ValueRepository

        repo = ValueRepository(data_dir=data_dir)
        repo.add_values(self.values())
        return repo

    def export(self, path: Union[str, Path]) -> Path:
        """Write the merged universe as one canonical, deterministic JSON file."""
        path = Path(path)
        docs = sorted(self.documents, key=lambda d: str(d.get("id", "")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(docs, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path


def _merge_named_node(
    name: str,
    contributors: List[Tuple[str, Dict[str, Any]]],
    on_conflict: str,
    report: MergeReport,
) -> Dict[str, Any]:
    """Reconcile several same-named node docs into one, recording divergence."""
    labels = [label for label, _ in contributors]
    kinds = {label: doc.get("kind") for label, doc in contributors}
    distinct_kinds = set(kinds.values())

    winner_idx = -1 if on_conflict == "last" else 0
    base = copy.deepcopy(contributors[winner_idx][1])

    # Record + resolve a type (kind) conflict.
    if len(distinct_kinds) > 1:
        report.type_conflicts[name] = dict(kinds)
        if on_conflict == "raise":
            raise ValueError(
                f"cannot merge node {name!r}: conflicting kinds {sorted(distinct_kinds)}"
            )

    # Reconcile the descriptive fields.
    ordered = contributors if on_conflict != "last" else list(reversed(contributors))
    for field in _MERGE_FIELDS:
        present = [(label, doc.get(field)) for label, doc in contributors if doc.get(field) is not None]
        distinct = {json.dumps(v, sort_keys=True) for _, v in present}
        if len(distinct) > 1:
            report.field_conflicts.setdefault(name, {})[field] = {
                label: val for label, val in present
            }
            if on_conflict == "raise":
                raise ValueError(
                    f"cannot merge node {name!r}: conflicting {field} across sources"
                )
        # Fill the winner's missing field from the first (by policy order) non-null.
        if base.get(field) is None:
            for _, doc in ordered:
                if doc.get(field) is not None:
                    base[field] = copy.deepcopy(doc.get(field))
                    break

    report.join_points[name] = labels
    return base


def merge_ontologies(
    sources: Sequence[SourceSpec],
    *,
    labels: Optional[Sequence[str]] = None,
    on_conflict: str = "first",
    dedupe_edges: bool = True,
) -> MergeResult:
    """Merge several ontologies into one universe, joining common nodes by name.

    ``sources`` may each be a path to a canonical ontology JSON file, a
    :class:`~valuez.repository.ValueRepository`, or an iterable of
    :class:`~valuez.values.Value` objects / document dicts.

    ``labels`` optionally names the sources (for the report); by default a file
    source is labelled by its filename stem, others ``source_<i>``.

    ``on_conflict`` decides how to reconcile a node whose contributors disagree
    on a descriptive field (or ``kind``): ``"first"`` keeps the first source's
    value (default), ``"last"`` the last, and ``"raise"`` refuses to merge.

    ``dedupe_edges`` (default ``True``) collapses identical edges asserted by
    more than one source into a single edge.
    """
    if on_conflict not in _CONFLICT_POLICIES:
        raise ValueError(f"on_conflict must be one of {_CONFLICT_POLICIES}")
    sources = list(sources)
    if labels is not None and len(labels) != len(sources):
        raise ValueError("labels must match the number of sources")

    report = MergeReport()

    # Pass 1: load + partition every source's documents.
    named: "Dict[str, List[Tuple[str, Dict[str, Any]]]]" = {}
    named_order: List[str] = []
    edge_docs: List[Tuple[str, Dict[str, Any]]] = []
    other_docs: List[Tuple[str, Dict[str, Any]]] = []

    for i, source in enumerate(sources):
        label, docs = _load_documents(source, i)
        if labels is not None:
            label = labels[i]
        # de-duplicate a label collision so the report stays unambiguous
        if label in report.input_counts:
            label = f"{label}_{i}"
        report.sources.append(label)
        report.input_counts[label] = len(docs)
        report.input_total += len(docs)
        for doc in docs:
            kind = doc.get("kind")
            if kind in NAME_NODE_KINDS:
                key = doc.get("name")
                if key is None:
                    other_docs.append((label, doc))
                    continue
                if key not in named:
                    named[key] = []
                    named_order.append(key)
                named[key].append((label, doc))
            elif kind in EDGE_KINDS:
                edge_docs.append((label, doc))
            else:
                other_docs.append((label, doc))

    # Pass 2: reconcile named nodes (join the overlaps).
    merged_nodes: List[Dict[str, Any]] = []
    for name in named_order:
        contributors = named[name]
        if len(contributors) == 1:
            merged_nodes.append(copy.deepcopy(contributors[0][1]))
        else:
            merged_nodes.append(_merge_named_node(name, contributors, on_conflict, report))
    node_names = {d.get("name") for d in merged_nodes}
    report.named_nodes_out = len(merged_nodes)

    # Pass 3: carry over edges, de-duplicating identical triples.
    report.edges_in = len(edge_docs)
    merged_edges: List[Dict[str, Any]] = []
    if dedupe_edges:
        seen: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        provenance: Dict[Tuple[Any, ...], List[str]] = {}
        for label, doc in edge_docs:
            key = _edge_key(doc)
            if key not in seen:
                seen[key] = copy.deepcopy(doc)
                provenance[key] = [label]
                merged_edges.append(seen[key])
            else:
                report.edges_deduped += 1
                if label not in provenance[key]:
                    provenance[key].append(label)
        report.shared_edges = [
            (key, labs) for key, labs in provenance.items() if len(labs) > 1
        ]
    else:
        merged_edges = [copy.deepcopy(doc) for _, doc in edge_docs]
    report.edges_out = len(merged_edges)

    # Report edges whose endpoints are not (any longer) present as nodes.
    for doc in merged_edges:
        for endpoint in (doc.get("source"), doc.get("target")):
            if endpoint is not None and endpoint not in node_names:
                report.dangling_edges.append((str(doc.get("id")), str(endpoint)))

    # Pass 4: assemble, then guarantee globally unique ids.
    assembled = merged_nodes + merged_edges + [copy.deepcopy(doc) for _, doc in other_docs]
    unique: List[Dict[str, Any]] = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for doc in assembled:
        doc_id = str(doc.get("id", ""))
        if doc_id not in by_id:
            by_id[doc_id] = doc
            unique.append(doc)
            continue
        if by_id[doc_id] == doc:
            continue  # exact duplicate document -> drop silently
        new_id = doc_id
        n = 2
        while new_id in by_id:
            new_id = f"{doc_id}__{n}"
            n += 1
        doc["id"] = new_id
        by_id[new_id] = doc
        unique.append(doc)
        report.id_collisions.append((doc_id, new_id))

    unique.sort(key=lambda d: str(d.get("id", "")))
    report.output_total = len(unique)
    return MergeResult(unique, report)
