"""Quantitative value primitives for the valuez semantic exploration platform.

This module defines the smallest traceable building blocks of the platform:

- :class:`Reference` -- a provenance pointer that lets any value be traced back
  to the source it was derived from, so data can be *ground-truthed*.
- :class:`Value` -- an abstract base carrying identity, an optional label/unit
  and an optional :class:`Reference`, plus dict (de)serialization so instances
  round-trip cleanly through ``dots`` JSON storage.
- :class:`Scalar` -- a single quantitative value.
- :class:`Range` -- a closed quantitative interval ``[low, high]``.

The classes are intentionally free of any ``dots`` import: they are pure domain
objects. Persistence and visualization are layered on top (see
``valuez.repository``), keeping the domain model testable in isolation while
still serializing into the shape ``dots`` expects (a JSON object with an ``id``).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional, Type, Union
import uuid

__all__ = ["Reference", "Value", "Scalar", "Range", "Number"]

Number = Union[int, float]


def _check_number(x: Any, name: str) -> Number:
    """Validate that ``x`` is a real number (rejecting ``bool``)."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise TypeError(f"{name} must be a real number, got {type(x).__name__}")
    return x


class Reference:
    """A traceable pointer to where a value came from.

    A reference is what makes a value *ground-truthable*: it records the source
    the value was taken from and, optionally, a finer-grained locator within
    that source, a human description, a subjective confidence in the ground
    truth (``0..1``), a retrieval timestamp, and arbitrary extra metadata.
    """

    def __init__(
        self,
        source: str,
        *,
        locator: Optional[str] = None,
        description: Optional[str] = None,
        confidence: Optional[float] = None,
        retrieved_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not source or not isinstance(source, str):
            raise ValueError("Reference.source must be a non-empty string")
        if confidence is not None and not (0.0 <= float(confidence) <= 1.0):
            raise ValueError("Reference.confidence must be within [0, 1]")
        self.source = source
        self.locator = locator
        self.description = description
        self.confidence = float(confidence) if confidence is not None else None
        self.retrieved_at = retrieved_at
        self.metadata: Dict[str, Any] = dict(metadata) if metadata else {}

    @classmethod
    def now(cls, source: str, **kwargs: Any) -> "Reference":
        """Build a reference stamped with the current UTC time."""
        kwargs.setdefault("retrieved_at", datetime.now(timezone.utc).isoformat())
        return cls(source, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"source": self.source}
        if self.locator is not None:
            data["locator"] = self.locator
        if self.description is not None:
            data["description"] = self.description
        if self.confidence is not None:
            data["confidence"] = self.confidence
        if self.retrieved_at is not None:
            data["retrieved_at"] = self.retrieved_at
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reference":
        return cls(
            source=data["source"],
            locator=data.get("locator"),
            description=data.get("description"),
            confidence=data.get("confidence"),
            retrieved_at=data.get("retrieved_at"),
            metadata=data.get("metadata") or {},
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Reference):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"Reference(source={self.source!r})"


class Value(ABC):
    """Abstract base for all traceable values.

    Concrete subclasses declare a unique ``kind`` discriminator and implement
    :meth:`_payload` (the value-specific fields) and :meth:`_from_payload`
    (reconstruction from a stored dict). Every value has a stable ``id`` so it
    maps 1:1 onto a ``dots`` storage document.
    """

    kind: ClassVar[str] = "value"
    _registry: ClassVar[Dict[str, Type["Value"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        kind = cls.__dict__.get("kind")
        if kind:
            Value._registry[kind] = cls

    def __init__(
        self,
        *,
        id: Optional[str] = None,
        label: Optional[str] = None,
        unit: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if reference is not None and not isinstance(reference, Reference):
            raise TypeError("reference must be a Reference instance or None")
        self.id: str = id or str(uuid.uuid4())
        self.label = label
        self.unit = unit
        self.reference = reference

    @abstractmethod
    def _payload(self) -> Dict[str, Any]:
        """Return the value-specific fields (e.g. ``{"value": 1.0}``)."""

    @classmethod
    @abstractmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Value":
        """Reconstruct a concrete value from a stored dict."""

    def is_grounded(self) -> bool:
        """Whether this value carries a reference it can be traced back to."""
        return self.reference is not None

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"id": self.id, "kind": self.kind}
        if self.label is not None:
            data["label"] = self.label
        if self.unit is not None:
            data["unit"] = self.unit
        data.update(self._payload())
        if self.reference is not None:
            data["reference"] = self.reference.to_dict()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Value":
        if cls is Value:
            kind = data.get("kind")
            target = cls._registry.get(kind)
            if target is None:
                raise ValueError(f"Unknown value kind: {kind!r}")
            return target.from_dict(data)
        ref_data = data.get("reference")
        reference = Reference.from_dict(ref_data) if ref_data else None
        return cls._from_payload(data, reference)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Value):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._payload()}, id={self.id!r})"


class Scalar(Value):
    """A single quantitative value (optionally with a unit)."""

    kind: ClassVar[str] = "scalar"

    def __init__(
        self,
        value: Number,
        *,
        unit: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id, label=label, unit=unit, reference=reference)
        self.value: Number = _check_number(value, "value")

    def _payload(self) -> Dict[str, Any]:
        return {"value": self.value}

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Scalar":
        return cls(
            data["value"],
            unit=data.get("unit"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )


class Range(Value):
    """A closed quantitative interval ``[low, high]``.

    Optionally carries a ``nominal`` (representative/expected) value that must
    fall within the interval.
    """

    kind: ClassVar[str] = "range"

    def __init__(
        self,
        low: Number,
        high: Number,
        *,
        nominal: Optional[Number] = None,
        unit: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
        id: Optional[str] = None,
    ) -> None:
        super().__init__(id=id, label=label, unit=unit, reference=reference)
        self.low: Number = _check_number(low, "low")
        self.high: Number = _check_number(high, "high")
        if self.low > self.high:
            raise ValueError(f"Range low ({self.low}) must be <= high ({self.high})")
        if nominal is not None:
            self.nominal: Optional[Number] = _check_number(nominal, "nominal")
            if not self.contains(self.nominal):
                raise ValueError(
                    f"Range nominal ({self.nominal}) must lie within [{self.low}, {self.high}]"
                )
        else:
            self.nominal = None

    @property
    def width(self) -> Number:
        return self.high - self.low

    @property
    def midpoint(self) -> float:
        return (self.low + self.high) / 2.0

    def contains(self, x: Number, *, inclusive: bool = True) -> bool:
        _check_number(x, "x")
        if inclusive:
            return self.low <= x <= self.high
        return self.low < x < self.high

    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"low": self.low, "high": self.high}
        if self.nominal is not None:
            payload["nominal"] = self.nominal
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Range":
        return cls(
            data["low"],
            data["high"],
            nominal=data.get("nominal"),
            unit=data.get("unit"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )
