import pytest

from valuez import Range, Reference, Scalar, Value


def test_scalar_basic_and_payload():
    s = Scalar(42.0, unit="kg", label="mass")
    assert s.value == 42.0
    assert s.unit == "kg"
    assert s.label == "mass"
    assert s.kind == "scalar"
    assert s.id  # auto-generated
    d = s.to_dict()
    assert d["kind"] == "scalar"
    assert d["value"] == 42.0
    assert d["unit"] == "kg"
    assert "reference" not in d


def test_scalar_rejects_non_numbers():
    with pytest.raises(TypeError):
        Scalar("not-a-number")
    with pytest.raises(TypeError):
        Scalar(True)  # bool is not a real number here


def test_range_geometry():
    r = Range(10, 20)
    assert r.low == 10 and r.high == 20
    assert r.width == 10
    assert r.midpoint == 15.0
    assert r.contains(15)
    assert r.contains(10) and r.contains(20)
    assert not r.contains(10, inclusive=False)
    assert not r.contains(25)


def test_range_invalid_bounds():
    with pytest.raises(ValueError):
        Range(20, 10)


def test_range_nominal_must_be_inside():
    r = Range(0, 100, nominal=50)
    assert r.nominal == 50
    with pytest.raises(ValueError):
        Range(0, 100, nominal=150)


def test_reference_ground_truthing():
    ref = Reference(
        source="lab-notebook-2026",
        locator="p.42",
        description="calibrated scale reading",
        confidence=0.95,
    )
    s = Scalar(3.14, reference=ref, label="pi-estimate")
    assert s.is_grounded()
    d = s.to_dict()
    assert d["reference"]["source"] == "lab-notebook-2026"
    assert d["reference"]["locator"] == "p.42"
    assert d["reference"]["confidence"] == 0.95


def test_reference_confidence_bounds():
    with pytest.raises(ValueError):
        Reference("src", confidence=1.5)


def test_reference_now_stamps_time():
    ref = Reference.now("sensor-A")
    assert ref.retrieved_at is not None


def test_ungrounded_value():
    assert not Scalar(1.0).is_grounded()


def test_scalar_roundtrip():
    ref = Reference("dataset://x", metadata={"row": 7})
    s = Scalar(2.5, unit="m", label="length", reference=ref, id="len-1")
    restored = Value.from_dict(s.to_dict())
    assert isinstance(restored, Scalar)
    assert restored == s
    assert restored.id == "len-1"
    assert restored.reference == ref
    assert restored.reference.metadata == {"row": 7}


def test_range_roundtrip():
    ref = Reference("spec-sheet", locator="table-3")
    r = Range(-1, 1, nominal=0, unit="V", label="tolerance", reference=ref, id="tol-1")
    restored = Value.from_dict(r.to_dict())
    assert isinstance(restored, Range)
    assert restored == r
    assert restored.nominal == 0
    assert restored.reference == ref


def test_from_dict_dispatch_by_kind():
    scalar_doc = {"id": "a", "kind": "scalar", "value": 1}
    range_doc = {"id": "b", "kind": "range", "low": 0, "high": 5}
    assert isinstance(Value.from_dict(scalar_doc), Scalar)
    assert isinstance(Value.from_dict(range_doc), Range)


def test_from_dict_unknown_kind():
    with pytest.raises(ValueError):
        Value.from_dict({"id": "x", "kind": "nope"})
