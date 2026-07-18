"""valuez: a traceable semantic exploration platform built on ``dots``.

The public API currently exposes the quantitative value primitives. Storage and
visualization are provided by :class:`valuez.repository.ValueRepository`, an OOP
cover over the functional ``dots`` storage/query/graph layer.
"""
from __future__ import annotations

from . import units
from .qualitative import (
    Boolean,
    Categorical,
    Nominal,
    Ordinal,
    Qualitative,
    Textual,
    Vocabulary,
)
from .semantic import Concept, Relation, build_relation_graph, visualize_relations
from .units import pint_available, to_quantity, unit_registry, validate_unit
from .values import Number, Quantitative, Range, Reference, Scalar, Value

__version__ = "0.1.0"

__all__ = [
    "Reference",
    "Value",
    "Quantitative",
    "Scalar",
    "Range",
    "Number",
    "Qualitative",
    "Categorical",
    "Nominal",
    "Ordinal",
    "Boolean",
    "Textual",
    "Vocabulary",
    "Concept",
    "Relation",
    "build_relation_graph",
    "visualize_relations",
    "units",
    "pint_available",
    "unit_registry",
    "validate_unit",
    "to_quantity",
    "__version__",
]
