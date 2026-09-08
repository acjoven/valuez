"""valuez: a traceable semantic exploration platform built on ``dotz``.

The public API currently exposes the quantitative value primitives. Storage and
visualization are provided by :class:`valuez.repository.ValueRepository`, an OOP
cover over the functional ``dotz`` storage/query/graph layer.
"""
from __future__ import annotations

from . import bibliography, discovery, reasoning, traversal, units
from .bibliography import ReferenceRepository
from .discovery import Crossing, Discovery, discover
from .dataset import DataSet
from .function import Function, Sample
from .merge import MergeReport, MergeResult, merge_ontologies
from .metaphysics import Individual, Instantiation, MetaphysicalEntity, Universal
from .qualitative import (
    Boolean,
    Categorical,
    Nominal,
    Ordinal,
    Qualitative,
    Textual,
    Vocabulary,
)
from .reading import OntologyBuilder, Reading
from .traversal import Graph
from .semantic import (
    Argument,
    Concept,
    Proposition,
    Relation,
    build_argument_graph,
    build_relation_graph,
    visualize_arguments,
    visualize_relations,
)
from .units import pint_available, to_quantity, unit_registry, validate_unit
from .values import Number, Quantitative, Range, Reference, Scalar, Value

__version__ = "0.1.0"

__all__ = [
    "Reference",
    "Value",
    "Quantitative",
    "Scalar",
    "Range",
    "DataSet",
    "Sample",
    "Function",
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
    "Proposition",
    "Argument",
    "build_relation_graph",
    "visualize_relations",
    "build_argument_graph",
    "visualize_arguments",
    "MetaphysicalEntity",
    "Individual",
    "Universal",
    "Instantiation",
    "Reading",
    "OntologyBuilder",
    "Graph",
    "discover",
    "Discovery",
    "Crossing",
    "ReferenceRepository",
    "merge_ontologies",
    "MergeResult",
    "MergeReport",
    "reasoning",
    "traversal",
    "discovery",
    "units",
    "bibliography",
    "pint_available",
    "unit_registry",
    "validate_unit",
    "to_quantity",
    "__version__",
]
