"""A collection type for related quantitative values.

:class:`DataSet` groups related :class:`~valuez.Scalar` / :class:`~valuez.Range`
instances (e.g. several literature values for the same physical quantity).

Why not just a ``list``? A plain list carries no invariants and no domain
behavior. ``DataSet`` earns its place by adding four things a list cannot:

1. **Invariants** -- members must be quantitative (``Scalar`` / ``Range``) and,
   by default, share one unit, so aggregates are meaningful.
2. **Interval-aware aggregates** -- ``min`` / ``max`` / ``mean`` / ``span`` and
   an :meth:`envelope` treat a ``Range`` by its bounds, not a single number.
3. **Collection-level provenance** -- a ``DataSet`` is itself a
   :class:`~valuez.values.Value` (its own ``id`` / ``label`` / ``reference``)
   and persists as *one* ``dotz`` document, so a named, ground-truthed
   compilation stays a single citable unit instead of loose rows.
4. **List ergonomics anyway** -- it implements the sequence protocol
   (``len`` / iteration / indexing / slicing), so you rarely give anything up.

If none of those matter for a given use, a list is the right tool -- this class
is for when they do.
"""
from __future__ import annotations

from typing import Any, Callable, ClassVar, Dict, Iterable, Iterator, List, Optional, Union

from . import units
from .values import Number, Quantitative, Range, Reference, Scalar, Value

__all__ = ["DataSet"]


class DataSet(Value):
    """An ordered, unit-coherent collection of :class:`Scalar` / :class:`Range`."""

    kind: ClassVar[str] = "dataset"

    def __init__(
        self,
        members: Iterable[Quantitative] = (),
        *,
        unit: Optional[str] = None,
        require_uniform_units: bool = True,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        self.require_uniform_units = bool(require_uniform_units)
        self._declared_unit = units.validate_unit(unit)
        self._members: List[Quantitative] = []
        self.extend(members)

    # -- construction / mutation ------------------------------------------- #
    def add(self, member: Quantitative) -> "DataSet":
        """Append a member (validating type and, by default, unit). Returns self."""
        if not isinstance(member, Quantitative):
            raise TypeError(
                "DataSet members must be Scalar or Range (Quantitative) instances, "
                f"got {type(member).__name__}"
            )
        if self.require_uniform_units:
            current = self._effective_unit()
            has_reference_unit = bool(self._members) or self._declared_unit is not None
            if has_reference_unit and member.unit != current:
                raise ValueError(
                    f"member unit {member.unit!r} does not match dataset unit {current!r}"
                )
        self._members.append(member)
        return self

    def extend(self, members: Iterable[Quantitative]) -> "DataSet":
        """Append several members. Returns self."""
        for member in members:
            self.add(member)
        return self

    # -- unit ------------------------------------------------------------- #
    def _effective_unit(self) -> Optional[str]:
        if self._declared_unit is not None:
            return self._declared_unit
        for member in self._members:
            return member.unit
        return None

    @property
    def unit(self) -> Optional[str]:
        """The dataset's unit: the declared unit, else the members' shared unit."""
        return self._effective_unit()

    @property
    def members(self) -> tuple:
        """A read-only view of the members."""
        return tuple(self._members)

    # -- sequence protocol ------------------------------------------------- #
    def __len__(self) -> int:
        return len(self._members)

    def __iter__(self) -> Iterator[Quantitative]:
        return iter(self._members)

    def __getitem__(self, index: Union[int, slice]) -> Union[Quantitative, "DataSet"]:
        if isinstance(index, slice):
            return DataSet(
                self._members[index],
                unit=self._declared_unit,
                require_uniform_units=self.require_uniform_units,
                label=self.label,
            )
        return self._members[index]

    def __contains__(self, member: object) -> bool:
        return member in self._members

    # -- selection --------------------------------------------------------- #
    def filter(self, predicate: Callable[[Quantitative], bool]) -> "DataSet":
        """Return a new DataSet with the members satisfying ``predicate``."""
        return DataSet(
            [m for m in self._members if predicate(m)],
            unit=self._declared_unit,
            require_uniform_units=self.require_uniform_units,
            label=self.label,
        )

    def by_kind(self, kind: str) -> "DataSet":
        """Members of a single kind (``"scalar"`` or ``"range"``)."""
        return self.filter(lambda m: m.kind == kind)

    def grounded(self) -> "DataSet":
        """Only members that carry a :class:`Reference`."""
        return self.filter(lambda m: m.is_grounded())

    # -- aggregates -------------------------------------------------------- #
    @staticmethod
    def _low(member: Quantitative) -> Number:
        return member.low if isinstance(member, Range) else member.value

    @staticmethod
    def _high(member: Quantitative) -> Number:
        return member.high if isinstance(member, Range) else member.value

    @staticmethod
    def _nominal(member: Quantitative) -> Number:
        return member.nominal if isinstance(member, Range) else member.value

    def _guard(self, op: str) -> None:
        if not self._members:
            raise ValueError(f"{op}() requires a non-empty DataSet")
        distinct = {m.unit for m in self._members}
        if len(distinct) > 1:
            raise ValueError(
                f"{op}() requires uniform units; dataset has mixed units {distinct}"
            )

    def nominal_values(self) -> List[Number]:
        """The representative value of each member (Scalar value / Range nominal)."""
        return [self._nominal(m) for m in self._members]

    def min(self) -> Number:
        """The smallest lower bound across members (Range.low / Scalar.value)."""
        self._guard("min")
        return min(self._low(m) for m in self._members)

    def max(self) -> Number:
        """The largest upper bound across members (Range.high / Scalar.value)."""
        self._guard("max")
        return max(self._high(m) for m in self._members)

    def mean(self) -> float:
        """The arithmetic mean of the members' representative values."""
        self._guard("mean")
        values = self.nominal_values()
        return sum(values) / len(values)

    def span(self) -> Number:
        """Width of the overall envelope: ``max() - min()``."""
        return self.max() - self.min()

    def envelope(
        self,
        *,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
        id: Optional[str] = None,
    ) -> Range:
        """The :class:`Range` spanning all members' extremes ``[min(), max()]``."""
        self._guard("envelope")
        return Range(
            self.min(),
            self.max(),
            unit=self.unit,
            label=label if label is not None else (f"{self.label} (envelope)" if self.label else None),
            reference=reference,
            id=id,
        )

    def describe(self) -> Dict[str, Any]:
        """A small summary dict: count, unit, and (when non-empty) min/max/mean/span."""
        summary: Dict[str, Any] = {"count": len(self._members), "unit": self.unit}
        if self._members and len({m.unit for m in self._members}) == 1:
            summary.update(min=self.min(), max=self.max(), mean=self.mean(), span=self.span())
        return summary

    # -- persistence ------------------------------------------------------- #
    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"members": [m.to_dict() for m in self._members]}
        if self._declared_unit is not None:
            payload["unit"] = self._declared_unit
        if not self.require_uniform_units:
            payload["require_uniform_units"] = False
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "DataSet":
        members = [Value.from_dict(d) for d in data.get("members", [])]
        return cls(
            members,
            unit=data.get("unit"),
            require_uniform_units=data.get("require_uniform_units", True),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def __repr__(self) -> str:
        unit = f" {self.unit}" if self.unit else ""
        return f"DataSet(n={len(self._members)}{unit}, id={self.id!r})"
