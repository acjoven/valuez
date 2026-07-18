#!/usr/bin/env python3
"""Collecting related quantitative values with `DataSet`.

Worked example: the natural-convection heat-transfer coefficient of air, `h`,
reported across several sources as a mix of `Scalar` and `Range` values. This is
exactly the case where a plain list falls short and a `DataSet` earns its keep:

- it enforces that every member is quantitative and shares one unit;
- it computes *interval-aware* aggregates (the envelope spans Range bounds, not
  just point values);
- it is itself a ground-truthed `Value`, so the whole compilation persists as a
  single citable `dots` document.

Run:  python examples/dataset_htc.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import DataSet, Range, Reference, Scalar, Value  # noqa: E402
from valuez.repository import ValueRepository  # noqa: E402

UNIT = "W/(m^2*K)"


def htc_dataset() -> DataSet:
    """Compile literature values for h (air, free convection) into one DataSet."""
    ds = DataSet(
        unit=UNIT,
        label="h_air_free_convection",
        id="ds_h_air",
        reference=Reference("Compilation", description="Free-convection h of air, multiple sources"),
    )
    ds.extend([
        Range(2, 25, unit=UNIT, id="h_incropera",
              reference=Reference("Incropera & DeWitt, Fundamentals of Heat and Mass Transfer (6e)",
                                  locator="Table 1.1 (free convection, gases)")),
        Range(2.5, 25, unit=UNIT, id="h_tables",
              reference=Reference("Standard heat-transfer tables", locator="Air, free convection")),
        Range(3, 25, unit=UNIT, id="h_hvac",
              reference=Reference("HVAC Systems Encyclopedia (ingener.by)", locator="natural convection, gases")),
        Scalar(7.0, unit=UNIT, id="h_comsol",
               reference=Reference("COMSOL", description="representative computed h, laminar natural convection")),
    ])
    return ds


def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_dataset"))
    out_dir.mkdir(parents=True, exist_ok=True)
    repo = ValueRepository(data_dir=out_dir / "store")

    ds = htc_dataset()

    line = "-" * 68
    print(line)
    print(f"valuez example: DataSet of h (air, free convection) [{ds.unit}]")
    print(line)
    print(f"Members ({len(ds)}):")
    for m in ds:
        src = m.reference.source if m.is_grounded() else "-"
        if m.kind == "range":
            print(f"  [{m.low:>4}, {m.high:>4}]  nominal {m.nominal:>6.2f}   {src}")
        else:
            print(f"   {m.value:>10.2f}                {src}")
    print()

    env = ds.envelope()
    print(f"Envelope (min..max) : {env.low} .. {env.high} {ds.unit}")
    print(f"Mean of nominals    : {ds.mean():.2f} {ds.unit}")
    print(f"Span                : {ds.span()} {ds.unit}")
    print(f"Grounded members    : {len(ds.grounded())} / {len(ds)}")
    print(f"describe()          : {ds.describe()}")
    print()

    # The whole compilation persists as ONE document, not one row per source.
    repo.add_value(ds)
    print(f"Persisted ids in store: {repo._store.list_ids()}")
    reloaded = repo.get_value("ds_h_air")
    assert isinstance(reloaded, DataSet) and reloaded == ds
    print(f"Reloaded DataSet: {reloaded!r}; envelope max = {reloaded.max()} {reloaded.unit}")
    print(line)


if __name__ == "__main__":
    main()
