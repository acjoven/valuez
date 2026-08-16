"""Contextualized quantitative data: empirical functions of one or more variables.

Where :class:`~valuez.DataSet` is a bag of values of *one* quantity, a
:class:`Function` records how a measured quantity depends on the *conditions* it
was measured at. Each observation is a :class:`Sample` mapping named input
coordinates (the independent variables) to an output value; a :class:`Function`
is an ordered, schema-coherent collection of such samples.

Examples
--------
- A heat capacity measured at several temperatures -> a 1-D ``cp(T)`` function.
- Reaction conversion measured across conditions -> a 3-D
  ``conversion(temperature, pressure, space_velocity)`` function.

Every coordinate and output is a :class:`~valuez.Scalar` or :class:`~valuez.Range`,
so individual points stay unit-checked and ground-truthable, and the whole
function persists as a single ``dotz`` document.

What a :class:`Function` adds over a list of tuples:

- **Schema coherence** -- every sample shares the same variable names, per-axis
  units, and output unit.
- **Evaluation** -- 1-D linear :meth:`interpolate` (and ``__call__``), plus
  :meth:`nearest` / :meth:`at` lookups for any arity.
- **Slicing the domain** -- :meth:`section` fixes some variables to project a
  lower-dimensional function (e.g. conversion vs. T at fixed P and space velocity).
- **Domain/range envelopes** and a :meth:`describe` summary.
- **Single-document provenance** -- it is itself a ground-truthable ``Value``.
"""
from __future__ import annotations

from typing import Any, Callable, ClassVar, Dict, Iterable, Iterator, List, Mapping, Optional, Tuple, Union

from . import units
from .values import Number, Quantitative, Range, Reference, Scalar, Value

__all__ = ["Sample", "Function"]


def _nominal(q: Quantitative) -> Number:
    return q.nominal if isinstance(q, Range) else q.value


def _low(q: Quantitative) -> Number:
    return q.low if isinstance(q, Range) else q.value


def _high(q: Quantitative) -> Number:
    return q.high if isinstance(q, Range) else q.value


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


class Sample(Value):
    """One observation: named input coordinates mapped to an output value.

    ``inputs`` is a mapping of variable name -> :class:`~valuez.Scalar` /
    :class:`~valuez.Range`; ``output`` is the measured value (also a Scalar/Range).
    """

    kind: ClassVar[str] = "sample"

    def __init__(
        self,
        inputs: Mapping[str, Quantitative],
        output: Quantitative,
        *,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        if not isinstance(inputs, Mapping) or not inputs:
            raise ValueError("Sample.inputs must be a non-empty mapping of name -> Quantitative")
        self.inputs: Dict[str, Quantitative] = {}
        for name, q in inputs.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Sample input names must be non-empty strings")
            if not isinstance(q, Quantitative):
                raise TypeError(f"input {name!r} must be a Scalar or Range, got {type(q).__name__}")
            self.inputs[name] = q
        if not isinstance(output, Quantitative):
            raise TypeError(f"Sample.output must be a Scalar or Range, got {type(output).__name__}")
        self.output = output

    def coords(self) -> Dict[str, Number]:
        """The representative (nominal) value of each input coordinate."""
        return {name: _nominal(q) for name, q in self.inputs.items()}

    def value(self) -> Number:
        """The representative (nominal) output value."""
        return _nominal(self.output)

    def _payload(self) -> Dict[str, Any]:
        return {
            "inputs": {name: q.to_dict() for name, q in self.inputs.items()},
            "output": self.output.to_dict(),
        }

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Sample":
        inputs = {name: Value.from_dict(d) for name, d in data["inputs"].items()}
        return cls(
            inputs,
            Value.from_dict(data["output"]),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def __repr__(self) -> str:
        coords = ", ".join(f"{k}={v}" for k, v in self.coords().items())
        return f"Sample({coords} -> {self.value()}, id={self.id!r})"


class Function(Value):
    """An ordered, schema-coherent collection of :class:`Sample` observations."""

    kind: ClassVar[str] = "function"

    def __init__(
        self,
        samples: Iterable[Sample] = (),
        *,
        variables: Optional[Iterable[str]] = None,
        input_units: Optional[Mapping[str, Optional[str]]] = None,
        output_unit: Optional[str] = None,
        output_label: Optional[str] = None,
        require_uniform_units: bool = True,
        id: Optional[str] = None,
        label: Optional[str] = None,
        reference: Optional[Reference] = None,
    ) -> None:
        super().__init__(id=id, label=label, reference=reference)
        self.require_uniform_units = bool(require_uniform_units)
        self.output_label = output_label
        self._variables: Optional[List[str]] = list(variables) if variables is not None else None
        self._input_units: Dict[str, Optional[str]] = {
            k: units.validate_unit(v) for k, v in (input_units or {}).items()
        }
        self._output_unit: Optional[str] = units.validate_unit(output_unit)
        self._output_frozen: bool = output_unit is not None
        self._samples: List[Sample] = []
        self.extend(samples)

    # -- construction / mutation ------------------------------------------ #
    def add(self, sample: Sample) -> "Function":
        """Append a sample, validating schema (variable names) and units. Returns self."""
        if not isinstance(sample, Sample):
            raise TypeError(f"Function members must be Sample instances, got {type(sample).__name__}")
        names = list(sample.inputs.keys())
        if self._variables is None:
            self._variables = names
        elif set(names) != set(self._variables):
            raise ValueError(
                f"sample variables {sorted(names)} do not match function schema {sorted(self._variables)}"
            )
        for name in self._variables:
            q = sample.inputs[name]
            if name in self._input_units:
                expected = self._input_units[name]
                if self.require_uniform_units and q.unit != expected:
                    raise ValueError(
                        f"axis {name!r} unit {q.unit!r} does not match function unit {expected!r}"
                    )
            else:
                self._input_units[name] = q.unit
        out_unit = sample.output.unit
        if not self._output_frozen:
            self._output_unit = out_unit
            self._output_frozen = True
        elif self.require_uniform_units and out_unit != self._output_unit:
            raise ValueError(
                f"output unit {out_unit!r} does not match function output unit {self._output_unit!r}"
            )
        self._samples.append(sample)
        return self

    def extend(self, samples: Iterable[Sample]) -> "Function":
        for sample in samples:
            self.add(sample)
        return self

    def _coerce(self, val: Union[Number, Quantitative], unit: Optional[str], field: str) -> Quantitative:
        if isinstance(val, Quantitative):
            return val
        if _is_number(val):
            return Scalar(val, unit=unit)
        raise TypeError(f"{field} must be a number or a Scalar/Range, got {type(val).__name__}")

    def record(self, output: Union[Number, Quantitative], /, **coords: Union[Number, Quantitative]) -> "Function":
        """Ergonomically add a point: numbers are coerced to Scalars using the
        declared axis / output units. E.g. ``f.record(75.3, temperature=300)``.
        """
        if not coords:
            raise ValueError("record() requires at least one input coordinate")
        inputs = {name: self._coerce(val, self._input_units.get(name), name) for name, val in coords.items()}
        out = self._coerce(output, self._output_unit if self._output_frozen else None, "output")
        return self.add(Sample(inputs, out))

    # -- schema ----------------------------------------------------------- #
    @property
    def variables(self) -> Tuple[str, ...]:
        return tuple(self._variables or ())

    @property
    def arity(self) -> int:
        return len(self._variables or ())

    @property
    def output_unit(self) -> Optional[str]:
        return self._output_unit if self._output_frozen else None

    def input_unit(self, name: str) -> Optional[str]:
        return self._input_units.get(name)

    @property
    def samples(self) -> tuple:
        return tuple(self._samples)

    # -- sequence protocol ------------------------------------------------ #
    def __len__(self) -> int:
        return len(self._samples)

    def __iter__(self) -> Iterator[Sample]:
        return iter(self._samples)

    def __getitem__(self, index: Union[int, slice]) -> Union[Sample, "Function"]:
        if isinstance(index, slice):
            return self._respawn(self._samples[index])
        return self._samples[index]

    def __contains__(self, sample: object) -> bool:
        return sample in self._samples

    def _respawn(self, samples: Iterable[Sample], variables: Optional[Iterable[str]] = None) -> "Function":
        """Build a derived Function that keeps this one's schema."""
        vars_ = list(variables) if variables is not None else (list(self._variables) if self._variables else None)
        return Function(
            samples,
            variables=vars_,
            input_units={k: self._input_units.get(k) for k in (vars_ or [])} or None,
            output_unit=self._output_unit if self._output_frozen else None,
            output_label=self.output_label,
            require_uniform_units=self.require_uniform_units,
            label=self.label,
        )

    # -- selection / projection ------------------------------------------- #
    def where(self, predicate: Callable[[Sample], bool]) -> "Function":
        """Return a new Function with the samples satisfying ``predicate``."""
        return self._respawn([s for s in self._samples if predicate(s)])

    def sorted_by(self, name: str, *, reverse: bool = False) -> "Function":
        """Return a new Function with samples ordered by an input axis's nominal."""
        self._check_axis(name)
        return self._respawn(sorted(self._samples, key=lambda s: _nominal(s.inputs[name]), reverse=reverse))

    def section(self, **fixed: Number) -> "Function":
        """Project to a lower-dimensional Function by fixing some variables.

        Selects samples whose fixed coordinates match (by nominal value) and
        drops those axes. E.g. ``f.section(pressure=1.0, space_velocity=1000)``
        yields conversion as a function of temperature alone.
        """
        for name in fixed:
            self._check_axis(name)
        remaining = [v for v in (self._variables or []) if v not in fixed]
        if not remaining:
            raise ValueError("section() must leave at least one free variable; use a DataSet for zero")
        picked: List[Sample] = []
        for s in self._samples:
            if all(_nominal(s.inputs[name]) == value for name, value in fixed.items()):
                picked.append(Sample({k: s.inputs[k] for k in remaining}, s.output,
                                     label=s.label, reference=s.reference))
        return self._respawn(picked, variables=remaining)

    # -- lookup / evaluation ---------------------------------------------- #
    def at(self, **coords: Number) -> Optional[Sample]:
        """Return the sample matching all coordinates exactly (by nominal), or None."""
        self._require_full_coords(coords)
        for s in self._samples:
            if all(_nominal(s.inputs[name]) == value for name, value in coords.items()):
                return s
        return None

    def nearest(self, **coords: Number) -> Sample:
        """Return the sample closest to ``coords`` (Euclidean distance, per-axis
        normalized by that axis's domain span)."""
        self._guard("nearest")
        self._require_full_coords(coords)
        spans = {name: (self.domain_envelope(name).width or 1.0) for name in self._variables or []}
        def distance(s: Sample) -> float:
            return sum(((_nominal(s.inputs[name]) - coords[name]) / spans[name]) ** 2
                       for name in self._variables or [])
        return min(self._samples, key=distance)

    def interpolate(self, x: Number) -> float:
        """Linear interpolation for a 1-D function (no extrapolation)."""
        if self.arity != 1:
            raise ValueError(f"interpolate() requires a 1-D function; this one has arity {self.arity}")
        self._guard("interpolate")
        axis = self._variables[0]
        pts = sorted(((_nominal(s.inputs[axis]), _nominal(s.output)) for s in self._samples))
        xs = [p[0] for p in pts]
        if not (xs[0] <= x <= xs[-1]):
            raise ValueError(f"x={x} is outside the domain [{xs[0]}, {xs[-1]}] (no extrapolation)")
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                if x1 == x0:
                    return float(y0)
                t = (x - x0) / (x1 - x0)
                return float(y0 + t * (y1 - y0))
        return float(pts[-1][1])

    def __call__(self, *args: Number, **kwargs: Number) -> float:
        if self.arity == 1:
            if len(args) == 1 and not kwargs:
                return self.interpolate(args[0])
            if not args and set(kwargs) == set(self._variables or []):
                return self.interpolate(next(iter(kwargs.values())))
            raise TypeError(f"1-D function takes one value for {self._variables}")
        raise TypeError(
            f"multi-dimensional Function is not directly callable; use .nearest(**coords) "
            f"or .at(**coords). variables={list(self.variables)}"
        )

    # -- aggregates ------------------------------------------------------- #
    def coordinates(self) -> List[Dict[str, Number]]:
        return [s.coords() for s in self._samples]

    def outputs(self) -> List[Number]:
        return [s.value() for s in self._samples]

    def domain_envelope(self, name: str) -> Range:
        """The [min low, max high] Range of an input axis across all samples."""
        self._check_axis(name)
        self._guard("domain_envelope")
        lows = [_low(s.inputs[name]) for s in self._samples]
        highs = [_high(s.inputs[name]) for s in self._samples]
        return Range(min(lows), max(highs), unit=self.input_unit(name), label=name)

    def output_envelope(self) -> Range:
        """The [min low, max high] Range of the output across all samples."""
        self._guard("output_envelope")
        lows = [_low(s.output) for s in self._samples]
        highs = [_high(s.output) for s in self._samples]
        return Range(min(lows), max(highs), unit=self.output_unit, label=self.output_label)

    def describe(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "n": len(self._samples),
            "variables": list(self.variables),
            "arity": self.arity,
            "input_units": {k: self._input_units.get(k) for k in (self._variables or [])},
            "output_unit": self.output_unit,
        }
        if self._samples:
            summary["domain"] = {name: (self.domain_envelope(name).low, self.domain_envelope(name).high)
                                 for name in self._variables or []}
            env = self.output_envelope()
            summary["output"] = (env.low, env.high)
        return summary

    # -- guards ----------------------------------------------------------- #
    def _check_axis(self, name: str) -> None:
        if name not in (self._variables or []):
            raise KeyError(f"unknown variable {name!r}; variables are {list(self.variables)}")

    def _require_full_coords(self, coords: Mapping[str, Number]) -> None:
        if set(coords) != set(self._variables or []):
            raise ValueError(f"expected coordinates for all of {list(self.variables)}, got {sorted(coords)}")

    def _guard(self, op: str) -> None:
        if not self._samples:
            raise ValueError(f"{op}() requires a non-empty Function")
        if self.require_uniform_units:
            return
        for name in self._variables or []:
            if len({s.inputs[name].unit for s in self._samples}) > 1:
                raise ValueError(f"{op}() requires uniform units on axis {name!r}")
        if len({s.output.unit for s in self._samples}) > 1:
            raise ValueError(f"{op}() requires uniform output units")

    # -- persistence ------------------------------------------------------ #
    def _payload(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "variables": list(self._variables or []),
            "samples": [s.to_dict() for s in self._samples],
        }
        if self._variables:
            payload["input_units"] = {k: self._input_units.get(k) for k in self._variables}
        if self._output_frozen:
            payload["output_unit"] = self._output_unit
        if self.output_label is not None:
            payload["output_label"] = self.output_label
        if not self.require_uniform_units:
            payload["require_uniform_units"] = False
        return payload

    @classmethod
    def _from_payload(cls, data: Dict[str, Any], reference: Optional[Reference]) -> "Function":
        samples = [Value.from_dict(d) for d in data.get("samples", [])]
        return cls(
            samples,
            variables=data.get("variables") or None,
            input_units=data.get("input_units"),
            output_unit=data.get("output_unit"),
            output_label=data.get("output_label"),
            require_uniform_units=data.get("require_uniform_units", True),
            label=data.get("label"),
            reference=reference,
            id=data.get("id"),
        )

    def __repr__(self) -> str:
        return f"Function({list(self.variables)} -> {self.output_label or 'output'}, n={len(self._samples)}, id={self.id!r})"
