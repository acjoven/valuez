"""A fluent authoring layer for building ontologies *as you read*.

The core :mod:`valuez` API (``Concept`` / ``Relation`` / ``Proposition`` /
``Argument`` + :class:`~valuez.repository.ValueRepository`) is expressive but
verbose to drive by hand: you repeat a :class:`~valuez.Reference` for every item
from the same passage, retype exact concept names on every edge (where a typo
only surfaces later), and hand-roll id generation, de-duplication, and
referential-integrity checks. The worked ``examples/kant_ontology.py`` builder
had to reinvent all of that scaffolding.

:class:`Reading` (aliased :class:`OntologyBuilder`) promotes that scaffolding
into the library. It is a *stateful session* that mirrors the reading
experience:

- **Citation context** -- ``with reading.at("A51/B75"):`` sets the provenance for
  everything created in the block, so you cite a passage once rather than on
  every call. The session's ``source`` (the text) is filled in automatically.
- **Create-or-reuse concepts** -- :meth:`concept` / :meth:`individual` /
  :meth:`universal` are keyed by name, so declaring the same term twice returns
  the same node (and can *enrich* a missing definition), never a duplicate.
- **Eager validation** -- :meth:`relate` checks that both endpoints already
  exist and that the predicate is in the controlled vocabulary *at the point of
  entry*, turning a late integrity sweep into an immediate, located error.
- **Automatic mechanics** -- deterministic ids, reference propagation, and
  one-call :meth:`export` / :meth:`render` over :class:`ValueRepository`.

The design principle: automate the *mechanics* aggressively (they involve no
judgment) while leaving the *content* -- which concept, which predicate, which
claim -- entirely to the reader. For a sketch of an optional, suggestion-only
LLM tier that feeds candidates into this same session, see
``docs/llm_assist.md``.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Type, Union

from .metaphysics import Individual, Instantiation, Universal
from .qualitative import Vocabulary
from .semantic import Argument, Concept, Proposition, Relation
from .values import Reference, Value

__all__ = ["Reading", "OntologyBuilder"]

ConceptRef = Union[str, Concept]
PropositionRef = Union[str, Proposition]


def _slug(name: str) -> str:
    """A filesystem/id-friendly slug of a concept name."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


class Reading:
    """A stateful, fluent session for building an ontology while reading a text.

    Parameters
    ----------
    source:
        The text being read (used as the default :class:`~valuez.Reference`
        source for everything created in an :meth:`at` block). Optional: without
        it you must pass a ``source`` to :meth:`at`, or items stay ungrounded.
    predicates:
        Optional controlled :class:`~valuez.Vocabulary` of allowed relation
        predicates. When given, :meth:`relate` rejects any predicate not in it.
    id_prefix:
        Prefix for generated, deterministic ids (e.g. ``"kant_"``). Ids are
        stable across runs given the same insertion order, so :meth:`export`
        produces minimal diffs.
    embed_vocabulary:
        If ``True``, embed the predicate vocabulary on every relation document
        (self-contained but larger). Default ``False``: validate at authoring
        time, keep stored edges lean.
    """

    def __init__(
        self,
        source: Optional[str] = None,
        *,
        predicates: Optional[Vocabulary] = None,
        id_prefix: str = "",
        embed_vocabulary: bool = False,
    ) -> None:
        if source is not None and (not isinstance(source, str) or not source):
            raise ValueError("source must be a non-empty string or None")
        if predicates is not None and not isinstance(predicates, Vocabulary):
            raise TypeError("predicates must be a Vocabulary instance or None")
        self.source = source
        self.predicates = predicates
        self.id_prefix = id_prefix
        self.embed_vocabulary = bool(embed_vocabulary)

        self._concepts: Dict[str, Concept] = {}
        self._relations: List[Relation] = []
        self._propositions: Dict[str, Proposition] = {}
        self._arguments: List[Argument] = []
        self._ref_stack: List[Reference] = []
        self._used_ids: set[str] = set()
        self._counters: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Citation context                                                   #
    # ------------------------------------------------------------------ #
    @contextmanager
    def at(
        self,
        locator: Optional[str] = None,
        *,
        source: Optional[str] = None,
        confidence: Optional[float] = None,
        description: Optional[str] = None,
        retrieved_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iterator["Reading"]:
        """Set the citation for everything created in the ``with`` block.

        ``locator`` is the fine-grained pointer into the text (page, section,
        Akademie pagination, ...). ``source`` overrides the session source for
        this block (e.g. quoting a secondary text). Nested blocks are allowed;
        the innermost citation wins.
        """
        src = source or self.source
        if src is None:
            raise ValueError(
                "no source available: construct Reading(source=...) or pass at(source=...)"
            )
        ref = Reference(
            src,
            locator=locator,
            description=description,
            confidence=confidence,
            retrieved_at=retrieved_at,
            metadata=metadata,
        )
        self._ref_stack.append(ref)
        try:
            yield self
        finally:
            self._ref_stack.pop()

    @contextmanager
    def cite(self, reference: Reference) -> Iterator["Reading"]:
        """Push an explicit, fully-formed :class:`~valuez.Reference` as context."""
        if not isinstance(reference, Reference):
            raise TypeError("cite() requires a Reference instance")
        self._ref_stack.append(reference)
        try:
            yield self
        finally:
            self._ref_stack.pop()

    def _current_reference(self) -> Optional[Reference]:
        if not self._ref_stack:
            return None
        # Clone so each item owns an independent reference (no aliased metadata).
        return Reference.from_dict(self._ref_stack[-1].to_dict())

    # ------------------------------------------------------------------ #
    # Id generation                                                      #
    # ------------------------------------------------------------------ #
    def _unique_id(self, candidate: str) -> str:
        base = f"{self.id_prefix}{candidate}"
        if base not in self._used_ids:
            self._used_ids.add(base)
            return base
        n = 2
        while f"{base}_{n}" in self._used_ids:
            n += 1
        final = f"{base}_{n}"
        self._used_ids.add(final)
        return final

    def _counter_id(self, family: str) -> str:
        i = self._counters.get(family, 0)
        self._counters[family] = i + 1
        return self._unique_id(f"{family}_{i:04d}")

    # ------------------------------------------------------------------ #
    # Concepts (create-or-reuse, keyed by name)                          #
    # ------------------------------------------------------------------ #
    def _make_concept(
        self,
        cls: Type[Concept],
        name: str,
        definition: Optional[str],
        ontological_status: Optional[str],
    ) -> Concept:
        if not isinstance(name, str) or not name:
            raise ValueError("concept name must be a non-empty string")
        existing = self._concepts.get(name)
        if existing is not None:
            if type(existing) is not cls:
                raise ValueError(
                    f"concept {name!r} already declared as {type(existing).__name__}, "
                    f"cannot redeclare as {cls.__name__}"
                )
            self._enrich(existing, "definition", definition)
            if ontological_status is not None:
                self._enrich(existing, "ontological_status", ontological_status)
            return existing
        kwargs: Dict[str, Any] = {
            "definition": definition,
            "id": self._unique_id(_slug(name)),
            "reference": self._current_reference(),
        }
        if cls is not Concept:
            kwargs["ontological_status"] = ontological_status
        obj = cls(name, **kwargs)
        self._concepts[name] = obj
        return obj

    @staticmethod
    def _enrich(obj: Any, attr: str, value: Optional[str]) -> None:
        """Fill a missing attribute; raise on a conflicting re-definition."""
        if value is None:
            return
        current = getattr(obj, attr, None)
        if current is None:
            setattr(obj, attr, value)
        elif current != value:
            raise ValueError(
                f"conflicting {attr} for {getattr(obj, 'name', obj)!r}: "
                f"{current!r} != {value!r}"
            )

    def concept(self, name: str, definition: Optional[str] = None) -> Concept:
        """Create or reuse a plain :class:`~valuez.Concept` node."""
        return self._make_concept(Concept, name, definition, None)

    def individual(
        self,
        name: str,
        definition: Optional[str] = None,
        *,
        ontological_status: Optional[str] = None,
    ) -> Individual:
        """Create or reuse an :class:`~valuez.Individual` (a particular)."""
        return self._make_concept(Individual, name, definition, ontological_status)  # type: ignore[return-value]

    def universal(
        self,
        name: str,
        definition: Optional[str] = None,
        *,
        ontological_status: Optional[str] = None,
    ) -> Universal:
        """Create or reuse a :class:`~valuez.Universal` (a kind/property)."""
        return self._make_concept(Universal, name, definition, ontological_status)  # type: ignore[return-value]

    def has(self, name: str) -> bool:
        """Whether a concept with this name has been declared."""
        return name in self._concepts

    def get(self, name: str) -> Concept:
        """Return the concept declared under ``name`` (raises if unknown)."""
        try:
            return self._concepts[name]
        except KeyError:
            raise KeyError(f"no concept named {name!r} has been declared") from None

    # ------------------------------------------------------------------ #
    # Relations (eager referential + vocabulary validation)              #
    # ------------------------------------------------------------------ #
    def _resolve_endpoint(self, ref: ConceptRef, field: str) -> str:
        """Return a registered concept name; register passed Concept objects."""
        if isinstance(ref, Concept):
            self._make_concept(
                type(ref), ref.name, ref.definition,
                getattr(ref, "ontological_status", None),
            )
            return ref.name
        if isinstance(ref, str) and ref:
            if ref not in self._concepts:
                raise ValueError(
                    f"{field} {ref!r} is not a declared concept; "
                    f"declare it first (e.g. reading.universal({ref!r}))"
                )
            return ref
        raise ValueError(f"{field} must be a non-empty concept name or Concept")

    def relate(
        self,
        source: ConceptRef,
        predicate: str,
        target: ConceptRef,
        *,
        modality: Optional[str] = None,
        strength: Optional[float] = None,
        label: Optional[str] = None,
    ) -> Relation:
        """Assert ``source --predicate--> target``, validating both eagerly.

        Both endpoints must already be declared concepts (pass a ``Concept``
        object to auto-declare). If the session has a predicate vocabulary, the
        predicate must be in it. ``instantiates`` is routed to
        :meth:`instantiate` so its typing is enforced.
        """
        if predicate == "instantiates":
            return self.instantiate(source, target, modality=modality,
                                     strength=strength, label=label)
        if not isinstance(predicate, str) or not predicate:
            raise ValueError("predicate must be a non-empty string")
        if self.predicates is not None and not self.predicates.contains(predicate):
            raise ValueError(
                f"predicate {predicate!r} is not in vocabulary {self.predicates.name!r}"
            )
        src = self._resolve_endpoint(source, "source")
        tgt = self._resolve_endpoint(target, "target")
        rel = Relation(
            src, predicate, tgt,
            vocabulary=self.predicates if self.embed_vocabulary else None,
            modality=modality, strength=strength, label=label,
            id=self._counter_id("rel"), reference=self._current_reference(),
        )
        self._relations.append(rel)
        return rel

    def instantiate(
        self,
        individual: ConceptRef,
        universal: ConceptRef,
        *,
        modality: Optional[str] = None,
        strength: Optional[float] = None,
        label: Optional[str] = None,
    ) -> Instantiation:
        """Assert a typed ``individual --instantiates--> universal`` edge."""
        src = self._resolve_endpoint(individual, "individual")
        tgt = self._resolve_endpoint(universal, "universal")
        src_obj, tgt_obj = self._concepts[src], self._concepts[tgt]
        if not isinstance(src_obj, Individual):
            raise TypeError(f"instantiation source {src!r} must be an Individual")
        if not isinstance(tgt_obj, Universal):
            raise TypeError(f"instantiation target {tgt!r} must be a Universal")
        inst = Instantiation(
            src_obj, tgt_obj, modality=modality, strength=strength, label=label,
            id=self._counter_id("inst"), reference=self._current_reference(),
        )
        self._relations.append(inst)
        return inst

    # ------------------------------------------------------------------ #
    # Propositions & arguments                                           #
    # ------------------------------------------------------------------ #
    def claim(
        self,
        statement: str,
        *,
        truth_value: Optional[bool] = None,
        label: Optional[str] = None,
    ) -> Proposition:
        """Record a reified, truth-apt claim (create-or-reuse by handle)."""
        handle = label or statement
        existing = self._propositions.get(handle)
        if existing is not None:
            if existing.statement != statement:
                raise ValueError(
                    f"proposition handle {handle!r} already used for a different statement"
                )
            if truth_value is not None:
                self._enrich(existing, "truth_value", truth_value)  # type: ignore[arg-type]
            return existing
        prop = Proposition(
            statement, truth_value=truth_value, label=label,
            id=self._counter_id("prop"), reference=self._current_reference(),
        )
        self._propositions[handle] = prop
        return prop

    def argue(
        self,
        premises: Iterable[PropositionRef],
        conclusion: PropositionRef,
        *,
        scheme: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Argument:
        """Record an argument from ``premises`` to a ``conclusion``.

        Premises/conclusion may be :class:`~valuez.Proposition` objects or bare
        handles. Passed ``Proposition`` objects are registered if new.
        """
        prem = [self._resolve_proposition(p) for p in premises]
        concl = self._resolve_proposition(conclusion)
        arg = Argument(
            prem, concl, scheme=scheme, label=label,
            id=self._counter_id("arg"), reference=self._current_reference(),
        )
        self._arguments.append(arg)
        return arg

    def _resolve_proposition(self, ref: PropositionRef) -> str:
        if isinstance(ref, Proposition):
            handle = ref.handle
            self._propositions.setdefault(handle, ref)
            return handle
        if isinstance(ref, str) and ref:
            return ref
        raise ValueError("premise/conclusion must be a non-empty handle or Proposition")

    # ------------------------------------------------------------------ #
    # Access                                                             #
    # ------------------------------------------------------------------ #
    @property
    def concepts(self) -> List[Concept]:
        return list(self._concepts.values())

    @property
    def individuals(self) -> List[Individual]:
        return [c for c in self._concepts.values() if isinstance(c, Individual)]

    @property
    def universals(self) -> List[Universal]:
        return [c for c in self._concepts.values() if isinstance(c, Universal)]

    @property
    def relations(self) -> List[Relation]:
        """All edges, including instantiations (which are typed relations)."""
        return list(self._relations)

    @property
    def instantiations(self) -> List[Instantiation]:
        return [r for r in self._relations if isinstance(r, Instantiation)]

    @property
    def propositions(self) -> List[Proposition]:
        return list(self._propositions.values())

    @property
    def arguments(self) -> List[Argument]:
        return list(self._arguments)

    def values(self) -> List[Value]:
        """Every persisted object: concepts, relations, propositions, arguments."""
        out: List[Value] = list(self._concepts.values())
        out.extend(self._relations)
        out.extend(self._propositions.values())
        out.extend(self._arguments)
        return out

    def node_names(self) -> set[str]:
        """Names that relation endpoints may reference."""
        return set(self._concepts.keys())

    def stats(self) -> Dict[str, int]:
        return {
            "concepts": len(self._concepts),
            "individuals": len(self.individuals),
            "universals": len(self.universals),
            "relations": len(self._relations),
            "instantiations": len(self.instantiations),
            "propositions": len(self._propositions),
            "arguments": len(self._arguments),
        }

    def __len__(self) -> int:
        return len(self.values())

    def __repr__(self) -> str:
        s = self.stats()
        return (
            f"Reading(source={self.source!r}, concepts={s['concepts']}, "
            f"relations={s['relations']}, propositions={s['propositions']}, "
            f"arguments={s['arguments']})"
        )

    # ------------------------------------------------------------------ #
    # Validation & reasoning                                             #
    # ------------------------------------------------------------------ #
    def validate(self) -> List[str]:
        """Return referential-integrity problems (empty means well-formed).

        ``relate`` already enforces this eagerly, so a clean session returns
        ``[]``; this is a defensive final sweep (e.g. after manual list edits).
        """
        names = self.node_names()
        problems: List[str] = []
        for r in self._relations:
            if r.source not in names:
                problems.append(f"{r.id}: unknown source {r.source!r}")
            if r.target not in names:
                problems.append(f"{r.id}: unknown target {r.target!r}")
        return problems

    def check(self) -> "Reading":
        """Raise if the ontology has integrity problems; else return self."""
        problems = self.validate()
        if problems:
            raise ValueError("integrity problems:\n  " + "\n  ".join(problems))
        return self

    def is_acyclic(self, predicate: str) -> bool:
        """Whether the ``predicate`` sub-graph is acyclic (a well-formed order)."""
        from . import reasoning

        return reasoning.is_acyclic(self._relations, predicate)

    def infer_transitive(self, predicate: str) -> List[Relation]:
        """Newly-entailed edges from the transitive closure of ``predicate``."""
        from . import reasoning

        return reasoning.infer_transitive(self._relations, predicate)

    def graph(self) -> Any:
        """Relation graph over this session, for neighborhood / path queries."""
        from .traversal import Graph

        return Graph.from_values(self.values())

    def analyze(self, **kwargs: Any) -> Any:
        """Inference + tension detection over this session. See :func:`valuez.analyze`."""
        from .analysis import analyze

        return analyze(self.values(), **kwargs)

    def explain(self, name: ConceptRef, **kwargs: Any) -> Any:
        """A readable :class:`~valuez.briefs.Brief` for one declared concept."""
        from .briefs import explain

        return explain(self.values(), name, **kwargs)

    # ------------------------------------------------------------------ #
    # Persistence & visualization                                        #
    # ------------------------------------------------------------------ #
    def to_repository(self, data_dir: Optional[Union[str, Path]] = None) -> Any:
        """Persist everything into a fresh :class:`ValueRepository` and return it."""
        from .repository import ValueRepository

        repo = ValueRepository(data_dir=data_dir)
        repo.add_values(self.values())
        return repo

    def bibliography(self, **kwargs: Any) -> Any:
        """Collect the cited bibliographic sources into a :class:`ReferenceRepository`.

        Only keyed sources are gathered by default; see
        :meth:`ReferenceRepository.from_values` for options.
        """
        from .bibliography import ReferenceRepository

        return ReferenceRepository.from_values(self.values(), **kwargs)

    def export(self, path: Union[str, Path], data_dir: Optional[Union[str, Path]] = None) -> Path:
        """Write the canonical single-file ontology JSON (the artifact to commit)."""
        return self.to_repository(data_dir=data_dir).export_ontology(path)

    def render(
        self,
        output_html: Union[str, Path],
        *,
        include_inferred: Optional[str] = None,
    ) -> Path:
        """Render the relation graph to interactive HTML.

        If ``include_inferred`` names a predicate, its transitive-closure edges
        are overlaid (styled as ``modality="inferred"``).
        """
        from .semantic import visualize_relations

        edges: List[Relation] = list(self._relations)
        if include_inferred:
            edges = edges + self.infer_transitive(include_inferred)
        return visualize_relations(edges, output_html)

    def render_arguments(self, output_html: Union[str, Path]) -> Path:
        """Render the argument map to interactive HTML."""
        from .semantic import visualize_arguments

        return visualize_arguments(self._arguments, output_html)


# Alias: the same session viewed as a generic builder rather than a "reading".
OntologyBuilder = Reading
