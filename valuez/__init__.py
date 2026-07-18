"""valuez: a traceable semantic exploration platform built on ``dots``.

The public API currently exposes the quantitative value primitives. Storage and
visualization are provided by :class:`valuez.repository.ValueRepository`, an OOP
cover over the functional ``dots`` storage/query/graph layer.
"""
from __future__ import annotations

from .values import Number, Range, Reference, Scalar, Value

__version__ = "0.1.0"

__all__ = [
    "Reference",
    "Value",
    "Scalar",
    "Range",
    "Number",
    "__version__",
]
