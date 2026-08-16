#!/usr/bin/env python3
"""Natural-convection cooling of stainless steel, built on valuez primitives.

A worked, source-backed engineering example for the valuez platform:

1. Collect *overall heat-transfer coefficient* (h) data for a stainless-steel
   surface losing heat to still air, from several online sources, encoding each
   datum as a :class:`~valuez.Scalar` or :class:`~valuez.Range` carrying a
   :class:`~valuez.Reference` (so every number is ground-truthed / traceable).
2. Collect AISI 304 stainless-steel thermal properties the same way.
3. Use the lumped-capacitance model (Newton's law of cooling) to compute how a
   300 C steel part cools in 25 C room air, propagating the *range* of h into a
   range of cooling rates and time constants.
4. Persist every input and derived value through ``dotz`` storage and emit a
   provenance graph linking each value to its source.

Physical model (lumped capacitance, valid when the Biot number Bi < 0.1):

    m*cp * dT/dt = -h*A*(T - T_inf)
    => T(t) = T_inf + (T0 - T_inf) * exp(-t / tau),   tau = rho*Lc*cp / h
    Lc = V/A  (characteristic length),  Bi = h*Lc/k

We treat the "overall" coefficient as the convective film coefficient h between
the surface and the air. Radiation is neglected here (a reasonable first cut at
moderate temperatures; it would add a parallel h_rad on the order of a few
W/m^2/K near 300 C and speed cooling somewhat).

Run:  python examples/heat_transfer_cooling.py
(Requires the sibling ``dotz`` package importable, e.g. ``pip install -e ../dotz``.)
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
from pathlib import Path

# Allow running as a plain script from anywhere in the repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Range, Reference, Scalar, Value  # noqa: E402
from valuez.repository import ValueRepository  # noqa: E402

HTC_UNIT = "W/(m^2*K)"

# --------------------------------------------------------------------------- #
# 1. Overall / natural-convection heat-transfer coefficient (air), by source. #
# --------------------------------------------------------------------------- #
def htc_data() -> list[Value]:
    return [
        Range(
            2, 25, unit=HTC_UNIT, id="htc_incropera", label="h_air_free_convection",
            reference=Reference(
                "Incropera & DeWitt, Fundamentals of Heat and Mass Transfer (6e), Table 1.1",
                locator="Free convection, Gases",
                description="Textbook typical range for free convection in gases.",
                confidence=0.95,
            ),
        ),
        Range(
            2.5, 25, unit=HTC_UNIT, id="htc_cengel", label="h_air_free_convection",
            reference=Reference(
                "Standard heat-transfer tables (Air, free convection)",
                locator="Air, free: 2.5-25 W/m^2K",
                description="Widely reproduced reference range for air free convection.",
                confidence=0.85,
            ),
        ),
        Range(
            3, 25, unit=HTC_UNIT, id="htc_hvac", label="h_air_free_convection",
            reference=Reference(
                "HVAC Systems Encyclopedia (ingener.by), Convection",
                locator="Natural (free) convection, gases",
                description="3-25 W/m^2K for gases.",
                confidence=0.7,
            ),
        ),
        Scalar(
            7.0, unit=HTC_UNIT, id="htc_comsol", label="h_air_free_convection_representative",
            reference=Reference(
                "COMSOL paper: HTC for a finned CPU heat sink under natural convection",
                locator="representative computed h ~= 7 W/m^2K (laminar)",
                confidence=0.6,
            ),
        ),
    ]


# --------------------------------------------------------------------------- #
# 2. AISI 304 stainless-steel thermal properties, by source.                  #
# --------------------------------------------------------------------------- #
def material_data() -> dict[str, Scalar]:
    return {
        "rho": Scalar(
            8000, unit="kg/m^3", id="ss304_density", label="ss304_density",
            reference=Reference(
                "MatWeb 304 Stainless Steel (8.00 g/cc); thepipingmart SS304 (8000 kg/m^3)",
                confidence=0.9,
            ),
        ),
        "cp": Scalar(
            500, unit="J/(kg*K)", id="ss304_cp", label="ss304_specific_heat",
            reference=Reference(
                "MatWeb 304 SS specific heat 0.500 J/g-C (0-100 C); AZoM Grade 304",
                confidence=0.9,
            ),
        ),
        "k": Scalar(
            16.2, unit="W/(m*K)", id="ss304_k", label="ss304_thermal_conductivity",
            reference=Reference(
                "MatWeb 304 SS thermal conductivity 16.2 W/m-K (0-100 C)",
                confidence=0.9,
            ),
        ),
    }


# --------------------------------------------------------------------------- #
# 3. Lumped-capacitance cooling model.                                        #
# --------------------------------------------------------------------------- #
def time_constant(h: float, rho: float, cp: float, Lc: float) -> float:
    """Cooling time constant tau = rho*Lc*cp / h  [s]."""
    return rho * Lc * cp / h


def initial_cooling_rate(h: float, rho: float, cp: float, Lc: float, dT: float) -> float:
    """Magnitude of dT/dt at t=0  [K/s] = (T0 - T_inf) / tau."""
    return dT / time_constant(h, rho, cp, Lc)


def time_to_temp(tau: float, T0: float, T_inf: float, T_target: float) -> float:
    """Time to cool from T0 to T_target in ambient T_inf  [s]."""
    return tau * math.log((T0 - T_inf) / (T_target - T_inf))


def biot(h: float, Lc: float, k: float) -> float:
    return h * Lc / k


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_heat_transfer"))
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = ValueRepository(data_dir=out_dir / "store")

    htcs = htc_data()
    mat = material_data()
    repo.add_values(htcs + list(mat.values()))

    # Scenario: a solid SS304 cube, 50 mm on a side, cooling in still room air.
    T0, T_inf = 300.0, 25.0            # degC
    dT = T0 - T_inf                    # 275 K temperature difference
    side = 0.05                        # m
    Lc = side / 6.0                    # V/A for a cube = L/6
    geom = Scalar(side, unit="m", id="geometry_cube_side", label="cube_side_length",
                  reference=Reference("Example scenario assumption (50 mm SS304 cube)",
                                      description="Solid cube, uniform properties."))
    repo.add_value(geom)

    rho, cp, k = mat["rho"].value, mat["cp"].value, mat["k"].value

    # Use the broadest well-cited textbook range (Incropera) as the working range.
    h_range = next(v for v in htcs if v.id == "htc_incropera")
    h_lo, h_hi, h_nom = h_range.low, h_range.high, h_range.nominal  # nominal = midpoint avg

    model_ref = Reference(
        "Derived: lumped-capacitance model (Newton's law of cooling)",
        description="tau = rho*Lc*cp/h; rate0 = dT/tau; T(t)=T_inf+dT*exp(-t/tau)",
        metadata={"inputs": ["htc_incropera", "ss304_density", "ss304_cp", "geometry_cube_side"]},
    )

    # Propagate the h range into derived ranges. Higher h -> faster cooling.
    rate_lo = initial_cooling_rate(h_lo, rho, cp, Lc, dT)
    rate_hi = initial_cooling_rate(h_hi, rho, cp, Lc, dT)
    tau_fast = time_constant(h_hi, rho, cp, Lc)
    tau_slow = time_constant(h_lo, rho, cp, Lc)

    cooling_rate = Range(rate_lo, rate_hi, unit="K/s", id="initial_cooling_rate",
                         label="initial_cooling_rate", reference=model_ref)
    tau_value = Range(tau_fast, tau_slow, unit="s", id="cooling_time_constant",
                      label="cooling_time_constant", reference=model_ref)
    repo.add_values([cooling_rate, tau_value])

    bi_lo, bi_hi = biot(h_lo, Lc, k), biot(h_hi, Lc, k)

    # ------------------------------------------------------------------ #
    # Report                                                             #
    # ------------------------------------------------------------------ #
    line = "-" * 68
    print(line)
    print("valuez example: natural-convection cooling of an SS304 cube")
    print(line)
    print(f"Scenario     : {side*1000:.0f} mm solid cube, T0 = {T0:.0f} degC, air T_inf = {T_inf:.0f} degC")
    print(f"Material     : AISI 304  (rho={rho:.0f} kg/m^3, cp={cp:.0f} J/kgK, k={k:.1f} W/mK)")
    print(f"Characteristic length Lc = V/A = L/6 = {Lc*1000:.2f} mm")
    print()
    print("Overall heat-transfer coefficient h (air, natural convection) by source:")
    for v in htcs:
        span = f"{v.low:g}-{v.high:g}" if isinstance(v, Range) else f"{v.value:g}"
        conf = v.reference.confidence
        conf_s = f", confidence={conf}" if conf is not None else ""
        print(f"  - {span:>9} {HTC_UNIT}  [{v.reference.source}{conf_s}]")
    print()
    print(f"Working range (Incropera Table 1.1): h = {h_lo:g}-{h_hi:g} {HTC_UNIT}"
          f" (midpoint {h_nom:g})")
    print()
    print("Lumped-capacitance validity (need Bi < 0.1):")
    print(f"  Bi = h*Lc/k ranges {bi_lo:.4f} (h={h_lo:g}) to {bi_hi:.4f} (h={h_hi:g})  -> "
          f"{'VALID' if bi_hi < 0.1 else 'INVALID'}")
    print()
    print("Results (propagating the h range):")
    print(f"  Initial cooling rate |dT/dt|_0 : {rate_lo*60:.2f} to {rate_hi*60:.2f} K/min"
          f"  ({rate_lo:.4f} to {rate_hi:.4f} K/s)")
    print(f"  Time constant tau              : {tau_fast/60:.1f} to {tau_slow/60:.1f} min"
          f"  ({tau_fast:.0f} to {tau_slow:.0f} s)")
    for target in (100.0, 50.0):
        t_fast = time_to_temp(tau_fast, T0, T_inf, target) / 60.0
        t_slow = time_to_temp(tau_slow, T0, T_inf, target) / 60.0
        print(f"  Time to reach {target:.0f} degC          : {t_fast:.0f} to {t_slow:.0f} min")
    print()

    # Confirm persistence + query through the dotz layer.
    stored = repo.query("[?kind=='range'] | length(@)")
    print(f"Persisted values in dotz store: {len(repo.query('[]'))} docs "
          f"({stored} ranges) at {out_dir / 'store'}")

    # Provenance graph: value label -> its ground-truth source.
    graph_path = _build_provenance_graph(repo, out_dir)
    if graph_path:
        print(f"Provenance graph: {graph_path}")
    print(line)


def _build_provenance_graph(repo: ValueRepository, out_dir: Path):
    """Emit a directed graph linking each stored value to its source (optional)."""
    try:
        from dotz.graph import build_graph_from_docs, visualize_graph
    except Exception:
        return None
    edges = []
    for doc in repo.query("[?reference]"):
        edges.append({"source": doc.get("label", doc["id"]),
                      "target": doc["reference"]["source"][:40]})
    g = build_graph_from_docs(edges, "source", "target")
    # pyvis writes a local ``lib/`` next to cwd; run from out_dir to keep repo clean.
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        return visualize_graph(g, Path("provenance.html")).resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
