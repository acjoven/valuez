"""valuez: a traceable semantic exploration platform built on ``dots``.

The public API currently exposes the quantitative value primitives. Storage and
visualization are provided by :class:`valuez.repository.ValueRepository`, an OOP
cover over the functional ``dots`` storage/query/graph layer.
"""
from __future__ import annotations

from . import units
from .qualitative import Categorical, Nominal, Ordinal, Qualitative, Vocabulary
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
    "Vocabulary",
    "units",
    "pint_available",
    "unit_registry",
    "validate_unit",
    "to_quantity",
    "__version__",
]
