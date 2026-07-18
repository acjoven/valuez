"""Qualitative value primitives for the valuez platform.

Where :mod:`valuez.values` covers numeric data (``Scalar`` / ``Range``), this
module covers *categorical* data — values drawn from a controlled set of terms:

- :class:`Vocabulary` -- a first-class, ground-truthable controlled vocabulary
  (the qualitative analogue of a unit). It lists the allowed terms, may be
  ordered, may define each term, and may carry its own :class:`Reference`.
- :class:`Qualitative` -- abstract base for non-numeric values (parallel to the
  numeric ``Quantitative`` base). Deliberately has no ``unit``.
- :class:`Categorical` -- abstract base for values that are a term, optionally
  validated against a :class:`Vocabulary`.
- :class:`Nominal` -- an unordered category (colour, material grade, ...).
- :class:`Ordinal` -- an ordered category (low/med/high, Likert, ...) supporting
  rank and comparison via an ordered vocabulary.

All of these reuse :class:`~valuez.values.Value`'s identity, reference-based
ground-truthing, ``kind`` registry, and dict (de)serialization, so they persist
through ``dots`` storage exactly like the numeric values.
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from .values import Reference, Value

__all__ = ["Vocabulary", "Qualitative", "Categorical", "Nominal", "Ordinal"]


class Vocabulary:
    """A controlled set of allowed terms (optionally ordered and defined).

    Serves as the qualitative counterpart to a physical unit: it constrains and
    gives meaning to a :class:`Categorical` value. Being ground-truthable (it can
    carry a :class:`Reference`), the *definitions* of the categories are traceable,
    not just the datum.
    """

    def __init__(
        self,
        name: str,
        terms: List[str],
        *,
        ordered: bool = False,
        definitions: Optional[Dict[str, str]] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if not name or not isinstance(name, str):
            raise ValueError("Vocabulary.name must be a non-empty string")
        terms = list(terms)
        if not terms:
            raise ValueError("Vocabulary needs at least one term")
        if any(not isinstance(t, str) or not t for t in terms):
            raise ValueError("Vocabulary terms must be non-empty strings")
        if len(set(terms)) != len(terms):
            raise ValueError("Vocabulary terms must be unique")
        if reference is not None and not isinstance(reference, Reference):
            raise TypeError("reference must be a Reference instance or None")
        self.name = name
        self.terms = terms
        self.ordered = bool(ordered)
        self.definitions: Dict[str, str] = dict(definitions) if definitions else {}
        self.reference = reference

    def contains(self, term: str) -> bool:
        return term in self.terms

    def rank(self, term: str) -> int:
        """Zero-based position of ``term`` (requires an ordered vocabulary)."""
        if not self.ordered:
            raise ValueError(f"Vocabulary {self.name!r} is not ordered")
        if term not in self.terms:
            raise ValueError(f"term {term!r} is not in vocabulary {self.name!r}")
        return self.terms.index(term)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "terms": list(self.terms),
            "ordered": self.ordered,
        }
        if self.definitions:
            data["definitions"] = dict(self.definitions)
        if self.reference is not None:
            data["reference"] = self.reference.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vocabulary":
        ref = data.get("reference")
        return cls(
            data["name"],
            data["terms"],
            ordered=data.get("ordered", False),
            definitions=data.get("definitions"),
            reference=Reference.from_dict(ref) if ref else None,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vocabulary):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        kind = "ordered" if self.ordered else "nominal"
        return f"Vocabulary(name={self.name!r}, {kind}, terms={self.terms!r})"


class Qualitative(Value):
    """Abstract base for non-numeric (categorical / textual) values."""


class Categorical(Qualitative):
    """Abstract base for a value that is a single ``term``.

    If a :class:`Vocabulary` is supplied, the term is validated against it and
    the vocabulary is embedded on serialization so the value stays self-contained.
    """

    def __init__(
        self,
        term: str,
        *,
        vocabulary: Optional[Vocabulary] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if type(self) is Categorical:
            raise TypeError("Categorical is abstract; use Nominal or Ordinal")
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(term, str) or not term:
            raise ValueError("term must be a non-empty string")
        if vocabulary is not None:
            if not isinstance(vocabulary, Vocabulary):
                raise TypeError("vocabulary must be a Vocabulary instance or None")
            if not vocabulary.contains(term):
                raise ValueError(
                    f"term {term!r} is not in vocabulary {vocabulary.name!r}"
                )
        self.term = term
        self.vocabulary = vocabulary

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"term": self.term}
        if self.vocabulary is not None:
            payload["vocabulary"] = self.vocabulary.to_dict()
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Categorical":
        vocab = data.get("vocabulary")
        vocabulary = Vocabulary.from_dict(vocab) if vocab else None
        return cls(
            data["term"],
            vocabulary=vocabulary,
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )


class Nominal(Categorical):
    """An unordered category (no meaningful ranking between terms)."""

    kind: ClassVar[str] = "nominal"


class Ordinal(Categorical):
    """An ordered category; supports rank and comparison.

    Requires an ordered :class:`Vocabulary` so that terms can be ranked.
    Comparisons are only defined between ordinals sharing the same term order.
    """

    kind: ClassVar[str] = "ordinal"

    def __init__(
        self,
        term: str,
        *,
        vocabulary: Vocabulary,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if not isinstance(vocabulary, Vocabulary) or not vocabulary.ordered:
            raise ValueError("Ordinal requires an ordered Vocabulary")
        super().__init__(term, vocabulary=vocabulary, id=id, label=label, reference=reference)

    @property
    def rank(self) -> int:
        return self.vocabulary.rank(self.term)

    def _comparable(self, other: object) -> bool:
        if not isinstance(other, Ordinal):
            return False
        if self.vocabulary.terms != other.vocabulary.terms:
            raise ValueError("cannot compare ordinals from different vocabularies")
        return True

    def __lt__(self, other: object) -> Any:
        if not self._comparable(other):
            return NotImplemented
        return self.rank < other.rank  # type: ignore[attr-defined]

    def __le__(self, other: object) -> Any:
        if not self._comparable(other):
            return NotImplemented
        return self.rank <= other.rank  # type: ignore[attr-defined]

    def __gt__(self, other: object) -> Any:
        if not self._comparable(other):
            return NotImplemented
        return self.rank > other.rank  # type: ignore[attr-defined]

    def __ge__(self, other: object) -> Any:
        if not self._comparable(other):
            return NotImplemented
        return self.rank >= other.rank  # type: ignore[attr-defined]
