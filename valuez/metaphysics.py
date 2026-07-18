"""Metaphysical primitives for valuez: particulars, universals, instantiation.

Where :mod:`valuez.semantic` gives an undifferentiated :class:`Concept`, a
metaphysical framework needs the defining distinction between *particulars* and
*universals*, and the *instantiation* relation that runs from the former to the
latter:

- :class:`MetaphysicalEntity` -- a :class:`Concept` that additionally records an
  optional ``ontological_status`` (its "mode of being": ``concrete`` /
  ``abstract``, ``fundamental`` / ``derivative``, ``actual`` / ``possible`` ...).
- :class:`Individual` -- a particular (e.g. *Socrates*, *this apple*).
- :class:`Universal` -- a kind / property / type (e.g. *Human*, *Redness*).
- :class:`Instantiation` -- a typed :class:`~valuez.Relation` whose predicate is
  fixed to ``instantiates`` and which (when given typed objects) enforces that
  its source is an :class:`Individual` and its target a :class:`Universal`.

For structural reasoning over orders such as parthood and grounding, see
:mod:`valuez.reasoning`.
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from .semantic import Concept, ConceptRef, Relation
from .values import Reference

__all__ = ["MetaphysicalEntity", "Individual", "Universal", "Instantiation"]


class MetaphysicalEntity(Concept):
    """A concept with an optional ``ontological_status`` (mode of being).

    Abstract: instantiate :class:`Individual` or :class:`Universal`.
    """

    def __init__(
        self,
        name: str,
        *,
        ontological_status: Optional[str] = None,
        definition: Optional[str] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if type(self) is MetaphysicalEntity:
            raise TypeError("MetaphysicalEntity is abstract; use Individual or Universal")
        super().__init__(name, definition=definition, id=id, label=label, reference=reference)
        if ontological_status is not None and (
            not isinstance(ontological_status, str) or not ontological_status
        ):
            raise ValueError("ontological_status must be a non-empty string or None")
        self.ontological_status = ontological_status

    def _payload(self) -> Dict[str, Any]:
        payload = super()._payload()
        if self.ontological_status is not None:
            payload["ontological_status"] = self.ontological_status
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "MetaphysicalEntity":
        return cls(
            data["name"],
            ontological_status=data.get("ontological_status"),
            definition=data.get("definition"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )


class Individual(MetaphysicalEntity):
    """A particular -- a concrete or abstract individual, not a kind."""

    kind: ClassVar[str] = "individual"


class Universal(MetaphysicalEntity):
    """A universal -- a kind, property, or type that can be instantiated."""

    kind: ClassVar[str] = "universal"


class Instantiation(Relation):
    """A typed ``instantiates`` edge: an :class:`Individual` instantiates a :class:`Universal`.

    When given typed objects the direction is enforced (only an Individual may
    instantiate, only a Universal may be instantiated). Bare names are accepted
    (e.g. when rehydrated from storage) and skip the type check.
    """

    kind: ClassVar[str] = "instantiation"

    def __init__(
        self,
        individual: ConceptRef,
        universal: ConceptRef,
        *,
        modality: Optional[str] = None,
        strength: Optional[float] = None,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        if isinstance(individual, Concept) and not isinstance(individual, Individual):
            raise TypeError("instantiation source must be an Individual (or a bare name)")
        if isinstance(universal, Concept) and not isinstance(universal, Universal):
            raise TypeError("instantiation target must be a Universal (or a bare name)")
        super().__init__(
            individual, "instantiates", universal,
            modality=modality, strength=strength, id=id, label=label, reference=reference,
        )

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Instantiation":
        return cls(
            data["source"],
            data["target"],
            modality=data.get("modality"),
            strength=data.get("strength"),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )
