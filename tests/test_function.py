"""Tests for Sample and Function (contextualized quantitative data)."""
import pytest

from valuez import Function, Range, Reference, Sample, Scalar, Value
from valuez.repository import ValueRepository


def cp_function() -> Function:
    """A 1-D heat capacity cp(T) with three points plus a ranged measurement."""
    f = Function(variables=["T"], input_units={"T": "K"},
                 output_unit="J/(mol*K)", output_label="cp", label="cp")
    f.record(29.1, T=300).record(29.3, T=400).record(29.6, T=500)
    f.add(Sample({"T": Scalar(600, unit="K")},
                 Range(29.8, 30.2, unit="J/(mol*K)"), reference=Reference("NIST")))
    return f


def conversion_function() -> Function:
    """A 3-D conversion(T, P, SV)."""
    f = Function(variables=["T", "P", "SV"],
                 input_units={"T": "K", "P": "bar", "SV": "1/hour"},
                 output_unit="dimensionless", output_label="conversion")
    f.record(0.42, T=600, P=1, SV=1000)
    f.record(0.55, T=650, P=1, SV=1000)
    f.record(0.61, T=650, P=5, SV=1000)
    f.record(0.48, T=650, P=1, SV=2000)
    return f


# --------------------------------------------------------------------------- #
# Sample                                                                       #
# --------------------------------------------------------------------------- #
def test_sample_requires_quantitative_inputs_and_output():
    with pytest.raises(TypeError):
        Sample({"T": 300}, Scalar(29.1))  # raw number input
    with pytest.raises(TypeError):
        Sample({"T": Scalar(300)}, 29.1)  # raw number output
    with pytest.raises(ValueError):
        Sample({}, Scalar(1.0))  # empty inputs


def test_sample_coords_and_value():
    s = Sample({"T": Scalar(300, unit="K")}, Range(29.8, 30.2, unit="J/(mol*K)"))
    assert s.coords() == {"T": 300}
    assert s.value() == pytest.approx(30.0)  # Range nominal = midpoint


def test_sample_roundtrip():
    s = Sample({"T": Scalar(300, unit="K")}, Scalar(29.1, unit="J/(mol*K)"), id="s1")
    restored = Value.from_dict(s.to_dict())
    assert isinstance(restored, Sample) and restored == s


# --------------------------------------------------------------------------- #
# Function schema / invariants                                                 #
# --------------------------------------------------------------------------- #
def test_schema_is_enforced():
    f = cp_function()
    with pytest.raises(ValueError):
        f.record(1.0, P=1)  # wrong variable name


def test_axis_unit_is_enforced():
    f = cp_function()
    with pytest.raises(ValueError):
        f.add(Sample({"T": Scalar(700, unit="degC")}, Scalar(30, unit="J/(mol*K)")))


def test_output_unit_is_enforced():
    f = cp_function()
    with pytest.raises(ValueError):
        f.add(Sample({"T": Scalar(700, unit="K")}, Scalar(30, unit="kg")))


def test_schema_inferred_from_first_sample():
    f = Function()
    f.add(Sample({"x": Scalar(1.0, unit="m")}, Scalar(2.0, unit="s")))
    assert f.variables == ("x",)
    assert f.input_unit("x") == "m"
    assert f.output_unit == "s"


# --------------------------------------------------------------------------- #
# Sequence protocol                                                            #
# --------------------------------------------------------------------------- #
def test_sequence_protocol():
    f = cp_function()
    assert len(f) == 4
    assert isinstance(f[0], Sample)
    assert isinstance(f[:2], Function) and len(f[:2]) == 2
    assert all(isinstance(s, Sample) for s in f)


# --------------------------------------------------------------------------- #
# 1-D evaluation                                                               #
# --------------------------------------------------------------------------- #
def test_interpolation_and_call():
    f = cp_function()
    assert f.arity == 1
    assert f(350) == pytest.approx(29.2)
    assert f.interpolate(450) == pytest.approx(29.45)
    assert f(T=300) == pytest.approx(29.1)  # exact node


def test_interpolation_rejects_extrapolation():
    f = cp_function()
    with pytest.raises(ValueError):
        f.interpolate(250)
    with pytest.raises(ValueError):
        f.interpolate(700)


# --------------------------------------------------------------------------- #
# multi-D lookup / projection                                                  #
# --------------------------------------------------------------------------- #
def test_nearest_and_at():
    f = conversion_function()
    assert f.nearest(T=648, P=1, SV=1000).value() == pytest.approx(0.55)
    assert f.at(T=650, P=5, SV=1000).value() == pytest.approx(0.61)
    assert f.at(T=999, P=1, SV=1000) is None
    with pytest.raises(ValueError):
        f.nearest(T=650)  # missing coordinates


def test_multidim_not_callable():
    f = conversion_function()
    with pytest.raises(TypeError):
        f(650)


def test_section_projects_to_lower_dimension():
    f = conversion_function()
    sec = f.section(P=1, SV=1000)
    assert sec.arity == 1 and sec.variables == ("T",)
    pts = [(s.coords()["T"], s.value()) for s in sec.sorted_by("T")]
    assert pts == [(600, pytest.approx(0.42)), (650, pytest.approx(0.55))]
    assert sec.output_unit == "dimensionless"


def test_section_requires_free_variable():
    f = cp_function()
    with pytest.raises(ValueError):
        f.section(T=300)


# --------------------------------------------------------------------------- #
# aggregates                                                                   #
# --------------------------------------------------------------------------- #
def test_domain_and_output_envelopes():
    f = cp_function()
    dom = f.domain_envelope("T")
    assert (dom.low, dom.high, dom.unit) == (300, 600, "K")
    out = f.output_envelope()
    assert (out.low, out.high) == (29.1, 30.2)  # includes the Range member's bounds


def test_describe():
    d = conversion_function().describe()
    assert d["arity"] == 3
    assert d["variables"] == ["T", "P", "SV"]
    assert d["domain"]["P"] == (1, 5)
    assert d["output"] == (pytest.approx(0.42), pytest.approx(0.61))


# --------------------------------------------------------------------------- #
# persistence                                                                  #
# --------------------------------------------------------------------------- #
def test_roundtrip_through_to_dict():
    for f in (cp_function(), conversion_function()):
        restored = Value.from_dict(f.to_dict())
        assert isinstance(restored, Function)
        assert restored == f
        assert restored.variables == f.variables


def test_persists_as_single_document(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    f = conversion_function()
    f.id = "conv-1"
    repo.add_value(f)
    assert repo._store.list_ids() == ["conv-1"]
    loaded = repo.get_value("conv-1")
    assert isinstance(loaded, Function)
    assert loaded == f
    assert loaded.at(T=650, P=5, SV=1000).value() == pytest.approx(0.61)
