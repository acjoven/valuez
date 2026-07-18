import pytest

from valuez import Range, Scalar
from valuez import units


def test_valid_unit_preserved_not_rewritten():
    # pint validates but valuez keeps the caller's original spelling.
    s = Scalar(5, unit="kg")
    assert s.unit == "kg"
    assert Scalar(5, unit=" m ").unit == "m"  # whitespace trimmed


def test_empty_unit_becomes_none():
    assert Scalar(1, unit="").unit is None
    assert Scalar(1).unit is None


@pytest.mark.skipif(not units.pint_available(), reason="pint not installed")
def test_invalid_unit_rejected():
    with pytest.raises(ValueError):
        Scalar(1, unit="not_a_real_unit")
    with pytest.raises(ValueError):
        Range(0, 1, unit="zorkmids")


def test_non_string_unit_type_error():
    with pytest.raises(TypeError):
        Scalar(1, unit=5)  # type: ignore[arg-type]


@pytest.mark.skipif(not units.pint_available(), reason="pint not installed")
def test_scalar_to_quantity():
    s = Scalar(2.0, unit="kg")
    q = s.to_quantity()
    assert q.magnitude == 2.0
    # Convertible via pint (dimensional handling works).
    assert pytest.approx(q.to("g").magnitude) == 2000.0


@pytest.mark.skipif(not units.pint_available(), reason="pint not installed")
def test_range_to_quantity_uses_nominal():
    r = Range(0, 10, unit="m")  # nominal defaults to 5.0
    q = r.to_quantity()
    assert q.magnitude == 5.0
    assert str(q.units) == "meter"


def test_to_quantity_without_pint(monkeypatch):
    # Simulate pint being unavailable and confirm a clear error.
    monkeypatch.setattr(units, "_UREG", None)
    with pytest.raises(RuntimeError):
        units.to_quantity(1.0, "kg")
