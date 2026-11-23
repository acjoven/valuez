#!/usr/bin/env python3
"""Merge two small maps of the same gas and see what the join creates.

Two chapters of the Feynman Lectures describe a gas from opposite ends:

- chapter 39 (kinetic theory) starts from molecules in motion;
- chapter 44 (thermodynamics) deliberately leaves the molecules out.

Each chapter becomes one small map, built with ``Reading``. They share four
names. ``Volume`` means the same thing in both. ``Temperature``, ``Pressure``,
and ``InternalEnergy`` do not: each chapter defines them in its own terms. That
is the hard case when joining maps, at a size you can read in one sitting.

The script then merges the two maps, prints the merge report, and lists the
*crossings*: short paths from a concept only one chapter mentions to a concept
only the other mentions, which exist only because the maps were joined.

Both chapters are free to read, so every definition and edge can be checked:
https://www.feynmanlectures.caltech.edu/I_39.html
https://www.feynmanlectures.caltech.edu/I_44.html

Run:  python examples/merge_demo.py

The run rewrites ``ontologies/thermodynamics.json`` and
``ontologies/kinetic_theory.json`` (the committed maps this script builds); the
merged map and its graph go to ``$VALUEZ_EXAMPLE_OUT``.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import Reading, Vocabulary, merge_ontologies  # noqa: E402

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"

LECTURES = "Feynman, Leighton & Sands, The Feynman Lectures on Physics, Vol. I (1963)"

# The textbook uses two names for the same substance: "ideal gas" in chapter 39,
# "perfect gas" in chapter 44. A curated alias joins them.
ALIASES = [["IdealGas", "PerfectGas"]]


def build_kinetic_theory() -> Reading:
    """Chapter 39: a gas as molecules in motion."""
    book = Reading(
        source=LECTURES,
        predicates=Vocabulary("kinetic_relations",
                              ["is-a", "made-of", "causes", "measures", "depends-on"]),
        id_prefix="kt_",
    )

    with book.at("39-2"):
        book.concept("Gas", "A lot of molecules in perpetual motion.")
        book.concept("Molecule", "One of the moving particles a gas is made of.")
        book.concept("MolecularCollision", "A molecule bouncing off a wall and handing it momentum.")
        book.concept("Pressure", "The momentum per second that molecular collisions deliver to a unit area of wall.")
        book.concept("Volume", "The space a substance occupies.")
        book.concept("MeanKineticEnergy", "The average kinetic energy of a molecule's center-of-mass motion.")
        book.concept("InternalEnergy", "The total energy of the molecules; for a monatomic gas, their kinetic energy.")
        book.relate("Gas", "made-of", "Molecule")
        book.relate("MolecularCollision", "causes", "Pressure")
        book.relate("Pressure", "depends-on", "MeanKineticEnergy")
        book.relate("Pressure", "depends-on", "Volume")
        book.relate("InternalEnergy", "depends-on", "MeanKineticEnergy")

    with book.at("39-4"):
        book.concept("Temperature", "A measure of the mean kinetic energy of a molecule.")
        book.relate("Temperature", "measures", "MeanKineticEnergy")
        book.claim("The mean molecular kinetic energy is a property only of the temperature.",
                   truth_value=True, label="P-MeanEnergy")

    with book.at("39-5"):
        book.concept("IdealGas", "A gas whose pressure, volume, and temperature obey PV = NkT.")
        book.relate("IdealGas", "is-a", "Gas")
        book.relate("Pressure", "depends-on", "Temperature")

    return book


def build_thermodynamics() -> Reading:
    """Chapter 44: the same gas, without mentioning what it is made of."""
    book = Reading(
        source=LECTURES,
        predicates=Vocabulary("thermodynamic_relations",
                              ["is-a", "changes", "governs", "converts", "produces",
                               "uses", "defines", "depends-on"]),
        id_prefix="td_",
    )

    with book.at("44-1"):
        book.concept("InternalEnergy", "The energy of a system; it rises by the heat put in plus the work done on it.")
        book.concept("Heat", "Energy put into a system other than by doing work on it.")
        book.concept("Work", "Energy put into a system by a force, as when a piston compresses a gas.")
        book.concept("FirstLaw", "Conservation of energy: heat in plus work done on a system is the rise in its energy.")
        book.relate("Heat", "changes", "InternalEnergy")
        book.relate("Work", "changes", "InternalEnergy")
        book.relate("FirstLaw", "governs", "InternalEnergy")

    with book.at("44-2"):
        book.concept("HeatEngine", "A device that takes in heat, does work, and delivers heat at a lower temperature.")
        book.concept("SecondLaw", "Heat cannot be turned into work at a single temperature with no other change.")
        book.relate("HeatEngine", "converts", "Heat")
        book.relate("HeatEngine", "produces", "Work")
        book.relate("SecondLaw", "governs", "HeatEngine")

    with book.at("44-3"):
        book.concept("ReversibleEngine", "An ideal, frictionless heat engine that a small change can run backwards.")
        book.concept("Pressure", "A property of the gas that falls as it expands at a fixed temperature.")
        book.concept("Volume", "The space a substance occupies.")
        book.relate("ReversibleEngine", "is-a", "HeatEngine")
        book.relate("Work", "depends-on", "Pressure")
        book.relate("Work", "depends-on", "Volume")
        book.claim("No engine can do more work than a reversible one.",
                   truth_value=True, label="P-Reversible")

    with book.at("44-4"):
        book.concept("PerfectGas", "The one substance whose laws are known, used to work out a reversible engine.")
        book.relate("ReversibleEngine", "uses", "PerfectGas")

    with book.at("44-5"):
        book.concept("Temperature", "How hot an object is, set by the heat a reversible engine absorbs from it.")
        book.relate("ReversibleEngine", "defines", "Temperature")

    with book.at("44-6"):
        book.concept("Entropy", "Heat absorbed divided by the temperature it is absorbed at.")
        book.relate("Entropy", "depends-on", "Heat")
        book.relate("Entropy", "depends-on", "Temperature")
        book.relate("Pressure", "depends-on", "Temperature")
        book.relate("Pressure", "depends-on", "Volume")
        book.relate("InternalEnergy", "depends-on", "Temperature")
        book.relate("InternalEnergy", "depends-on", "Volume")

    return book


def write_maps(directory: Path) -> Tuple[Path, Path]:
    """Export both maps as canonical JSON; returns (thermodynamics, kinetic_theory)."""
    directory = Path(directory)
    return (
        build_thermodynamics().check().export(directory / "thermodynamics.json"),
        build_kinetic_theory().check().export(directory / "kinetic_theory.json"),
    )


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_merge_demo"))
    out_dir.mkdir(parents=True, exist_ok=True)

    maps = list(write_maps(ONTOLOGIES))
    result = merge_ontologies(maps)
    report = result.report

    line = "-" * 72
    print(line)
    print("valuez merge demo: two maps of the same gas")
    print(line)
    print(report.summary())
    print()

    print("Same name, two definitions (the first source's is kept, both are reported):")
    for name in sorted(report.field_conflicts):
        definitions = report.field_conflicts[name].get("definition")
        if not definitions:
            continue
        print(f"  {name}")
        for source, definition in definitions.items():
            print(f"    {source:15s} {definition}")
    print()

    found = result.discover(cutoff=2, limit=0)
    crossings = found.between("thermodynamics", "kinetic_theory")
    print(f"Crossings: {len(crossings)} two-hop paths from a thermodynamics-only concept "
          f"to a kinetic-theory-only one")
    for crossing in crossings:
        print(f"  {crossing.path.describe()}")
    through = Counter(join for crossing in crossings for join in crossing.via)
    print("  through: " + ", ".join(f"{name} ({n})" for name, n in through.most_common()))
    print()

    aligned = merge_ontologies(maps, aliases=ALIASES)
    print("With a curated alias (IdealGas = PerfectGas):")
    print(f"  join points {report.join_point_count} -> {aligned.report.join_point_count}")
    for crossing in aligned.discover(cutoff=2, limit=0).between("thermodynamics", "kinetic_theory"):
        if "IdealGas" in crossing.via:
            print(f"  new crossing: {crossing.path.describe()}")
    print()

    graph = result.graph()

    universe = result.export(out_dir / "gas_universe.json")
    print(f"Merged map written: {universe}  ({report.output_total} docs)")

    try:
        import dotz.graph  # noqa: F401
        cwd = Path.cwd()
        try:
            os.chdir(out_dir)
            print(f"Graph: {graph.visualize('gas_universe.html').resolve()}")
        finally:
            os.chdir(cwd)
    except Exception as exc:  # pragma: no cover - visualization is optional
        print(f"(graph rendering skipped: {exc})")
    print(line)


if __name__ == "__main__":
    main()
