"""Guards the physics in examples/heat_transfer_cooling.py."""
import importlib.util
import math
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "heat_transfer_cooling",
    Path(__file__).resolve().parent.parent / "examples" / "heat_transfer_cooling.py",
)
htc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(htc)

# SS304 + 50 mm cube scenario.
RHO, CP, K = 8000.0, 500.0, 16.2
SIDE = 0.05
LC = SIDE / 6.0
T0, T_INF = 300.0, 25.0
DT = T0 - T_INF


def test_time_constant_and_rate_are_consistent():
    h = 10.0
    tau = htc.time_constant(h, RHO, CP, LC)
    # tau = rho*Lc*cp/h
    assert tau == pytest.approx(RHO * LC * CP / h)
    # initial rate = dT / tau
    assert htc.initial_cooling_rate(h, RHO, CP, LC, DT) == pytest.approx(DT / tau)


def test_biot_number_keeps_lumped_model_valid():
    # Across the whole textbook h range, Bi must stay < 0.1.
    assert htc.biot(2.0, LC, K) < htc.biot(25.0, LC, K) < 0.1


def test_time_to_temp_matches_exponential_decay():
    tau = htc.time_constant(10.0, RHO, CP, LC)
    t = htc.time_to_temp(tau, T0, T_INF, 100.0)
    # Plugging t back into the decay law recovers the target temperature.
    recovered = T_INF + DT * math.exp(-t / tau)
    assert recovered == pytest.approx(100.0)


def test_higher_h_cools_faster():
    slow = htc.time_constant(2.0, RHO, CP, LC)
    fast = htc.time_constant(25.0, RHO, CP, LC)
    assert fast < slow


def test_htc_and_material_data_are_grounded():
    for v in htc.htc_data():
        assert v.is_grounded()
        assert v.unit == "W/(m^2*K)"
    mat = htc.material_data()
    assert set(mat) == {"rho", "cp", "k"}
    assert all(v.is_grounded() for v in mat.values())
