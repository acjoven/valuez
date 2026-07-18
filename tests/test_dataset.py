"""Tests for the quantitative DataSet collection."""
import pytest

from valuez import DataSet, Range, Reference, Scalar, Value
from valuez.repository import ValueRepository


def _htc() -> DataSet:
    return DataSet(
        [
            Range(2, 25, unit="W/(m^2*K)", reference=Reference("Incropera")),
            Scalar(7.0, unit="W/(m^2*K)", reference=Reference("COMSOL")),
            Range(2.5, 25, unit="W/(m^2*K)"),
        ],
        label="h_air",
    )


# --------------------------------------------------------------------------- #
# invariants                                                                  #
# --------------------------------------------------------------------------- #
def test_rejects_non_quantitative_members():
    from valuez import Concept

    with pytest.raises(TypeError):
        DataSet([Concept("X")])


def test_enforces_uniform_units_by_default():
    ds = DataSet([Scalar(1.0, unit="kg")])
    with pytest.raises(ValueError):
        ds.add(Scalar(2.0, unit="g"))


def test_declared_unit_constrains_first_member():
    ds = DataSet(unit="kg")
    with pytest.raises(ValueError):
        ds.add(Scalar(1.0, unit="m"))
    ds.add(Scalar(1.0, unit="kg"))
    assert ds.unit == "kg"


def test_relaxed_mode_allows_mixed_units_but_guards_stats():
    ds = DataSet(require_uniform_units=False)
    ds.add(Scalar(1.0, unit="kg"))
    ds.add(Scalar(2.0, unit="m"))
    assert len(ds) == 2
    with pytest.raises(ValueError):
        ds.mean()


# --------------------------------------------------------------------------- #
# sequence protocol                                                           #
# --------------------------------------------------------------------------- #
def test_sequence_protocol():
    ds = _htc()
    assert len(ds) == 3
    assert [type(m).__name__ for m in ds] == ["Range", "Scalar", "Range"]
    assert isinstance(ds[1], Scalar)
    sub = ds[:2]
    assert isinstance(sub, DataSet) and len(sub) == 2
    assert ds[0] in ds


def test_add_and_extend_are_chainable():
    ds = DataSet(unit="m").add(Scalar(1.0, unit="m")).extend([Scalar(2.0, unit="m")])
    assert len(ds) == 2


# --------------------------------------------------------------------------- #
# aggregates                                                                  #
# --------------------------------------------------------------------------- #
def test_aggregates_are_interval_aware():
    ds = _htc()
    assert ds.min() == 2      # lowest Range.low
    assert ds.max() == 25     # highest Range.high
    assert ds.nominal_values() == [13.5, 7.0, 13.75]
    assert ds.mean() == pytest.approx((13.5 + 7.0 + 13.75) / 3)
    assert ds.span() == 23


def test_envelope_returns_spanning_range():
    ds = _htc()
    env = ds.envelope()
    assert isinstance(env, Range)
    assert (env.low, env.high) == (2, 25)
    assert env.unit == "W/(m^2*K)"
    assert "envelope" in env.label


def test_describe_summary():
    d = _htc().describe()
    assert d["count"] == 3
    assert d["unit"] == "W/(m^2*K)"
    assert d["min"] == 2 and d["max"] == 25 and d["span"] == 23


def test_empty_dataset_guards():
    ds = DataSet()
    assert len(ds) == 0
    assert ds.describe() == {"count": 0, "unit": None}
    for op in (ds.min, ds.max, ds.mean, ds.envelope):
        with pytest.raises(ValueError):
            op()


# --------------------------------------------------------------------------- #
# selection                                                                   #
# --------------------------------------------------------------------------- #
def test_selection_helpers():
    ds = _htc()
    assert len(ds.grounded()) == 2
    assert len(ds.by_kind("range")) == 2
    assert isinstance(ds.filter(lambda m: True), DataSet)


# --------------------------------------------------------------------------- #
# persistence                                                                 #
# --------------------------------------------------------------------------- #
def test_roundtrip_through_to_dict():
    ds = _htc()
    restored = Value.from_dict(ds.to_dict())
    assert isinstance(restored, DataSet)
    assert restored == ds
    assert [type(m).__name__ for m in restored] == ["Range", "Scalar", "Range"]


def test_persists_as_single_document(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    ds = _htc()
    ds.id = "htc-1"
    repo.add_value(ds)
    # one document for the whole collection, not one per member
    assert repo._store.list_ids() == ["htc-1"]
    loaded = repo.get_value("htc-1")
    assert isinstance(loaded, DataSet)
    assert loaded == ds
    assert loaded.max() == 25
