#!/usr/bin/env python3
"""Contextualized quantitative data with `Function`.

Two worked cases show how `Function` captures a measured quantity together with
the *conditions* it was measured at:

1. **1-D** -- molar heat capacity of N2 gas, cp(T), tabulated at several
   temperatures. Demonstrates linear interpolation between measured points.
2. **3-D** -- catalytic reaction conversion measured across
   (temperature, pressure, space_velocity). Demonstrates nearest-point lookup
   and `section(...)` to slice conversion vs. temperature at fixed conditions.

Each coordinate/value is a ground-truthed `Scalar`/`Range`, and each whole
function persists as a single `dots` document.

Run:  python examples/empirical_functions.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Function, Range, Reference, Sample, Scalar, Value  # noqa: E402
from valuez.repository import ValueRepository  # noqa: E402


def heat_capacity() -> Function:
    """cp(T) of N2 gas [J/(mol*K)] at several temperatures (NIST-Shomate order)."""
    nist = Reference("NIST Chemistry WebBook", locator="N2, Shomate equation")
    cp = Function(variables=["T"], input_units={"T": "K"},
                  output_unit="J/(mol*K)", output_label="cp", label="cp_N2(T)",
                  reference=Reference("Compilation", description="N2 molar heat capacity vs T"))
    for T, val in [(300, 29.12), (400, 29.25), (500, 29.58), (600, 30.11)]:
        cp.add(Sample({"T": Scalar(T, unit="K")}, Scalar(val, unit="J/(mol*K)"), reference=nist))
    return cp


def conversion() -> Function:
    """Reaction conversion(T, P, space_velocity), a 3-D empirical function."""
    lab = Reference("Lab notebook", locator="reactor run series A")
    f = Function(variables=["T", "P", "SV"],
                 input_units={"T": "K", "P": "bar", "SV": "1/hour"},
                 output_unit="dimensionless", output_label="conversion",
                 label="conversion(T,P,SV)",
                 reference=Reference("Compilation", description="Catalytic conversion sweep"))
    # (T, P, SV) -> conversion (with a couple of ranged, uncertain measurements)
    f.record(0.42, T=600, P=1, SV=1000)
    f.add(Sample({"T": Scalar(650, unit="K"), "P": Scalar(1, unit="bar"), "SV": Scalar(1000, unit="1/hour")},
                 Range(0.53, 0.57, unit="dimensionless"), reference=lab))
    f.record(0.61, T=700, P=1, SV=1000)
    f.record(0.68, T=650, P=5, SV=1000)
    f.record(0.47, T=650, P=1, SV=2000)
    return f


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_functions"))
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = ValueRepository(data_dir=out_dir / "store")

    line = "-" * 70
    cp = heat_capacity()
    print(line)
    print(f"1-D Function: {cp.label}  [{cp.output_unit} vs {cp.input_unit('T')}]")
    print(line)
    for s in cp:
        print(f"  T = {s.coords()['T']:>4} K   cp = {s.value():.2f}")
    print(f"  domain T : {cp.domain_envelope('T').low}..{cp.domain_envelope('T').high} K")
    print(f"  interpolated cp(350 K) = {cp(350):.3f} {cp.output_unit}")
    print(f"  interpolated cp(575 K) = {cp(575):.3f} {cp.output_unit}")
    print()

    conv = conversion()
    print(line)
    print(f"3-D Function: {conv.label}   arity={conv.arity}")
    print(line)
    print(f"  variables/units : {conv.describe()['input_units']}")
    print(f"  domain          : {conv.describe()['domain']}")
    for s in conv:
        c = s.coords()
        print(f"  T={c['T']:>4} P={c['P']:>2} SV={c['SV']:>5}  ->  conversion = {s.value():.3f}")
    print()
    near = conv.nearest(T=655, P=1, SV=1000)
    print(f"  nearest to (T=655,P=1,SV=1000) -> {near.value():.3f} at {near.coords()}")
    print(f"  exact at (T=650,P=5,SV=1000)   -> {conv.at(T=650, P=5, SV=1000).value():.3f}")
    print("  section P=1 bar, SV=1000 1/h  ->  conversion vs T:")
    for s in conv.section(P=1, SV=1000).sorted_by("T"):
        print(f"      T={s.coords()['T']:>4} K  ->  {s.value():.3f}")
    print()

    # Each whole function persists as ONE document.
    repo.add_values([cp, conv])
    print(f"Persisted functions as single docs: {sorted(repo.query('[?kind==`function`].id'))}")
    reloaded = repo.get_value(conv.id)
    assert isinstance(reloaded, Function) and reloaded == conv
    print(f"Reloaded {reloaded!r}")
    print(line)


if __name__ == "__main__":
    main()
