"""Integration tests: values persisted + queried through the dotz layer."""
from valuez import Range, Reference, Scalar
from valuez.repository import ValueRepository


def test_add_values_and_query(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    s = Scalar(42.0, unit="kg", label="mass", id="mass-1",
               reference=Reference("scale#7", confidence=0.9))
    r = Range(0, 100, nominal=50, unit="%", label="charge", id="charge-1",
              reference=Reference("bms-log", locator="t=12:00"))

    ids = repo.add_values([s, r])
    assert set(ids) == {"mass-1", "charge-1"}

    scalars = repo.query("[?kind=='scalar']")
    assert len(scalars) == 1
    assert scalars[0]["value"] == 42.0
    assert scalars[0]["reference"]["source"] == "scale#7"


def test_get_value_roundtrip_through_storage(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    r = Range(-5, 5, unit="C", label="temp", id="temp-1",
              reference=Reference.now("thermometer-3"))
    repo.add_value(r)

    loaded = repo.get_value("temp-1")
    assert isinstance(loaded, Range)
    assert loaded == r
    assert loaded.is_grounded()
    assert repo.get_value("missing") is None
