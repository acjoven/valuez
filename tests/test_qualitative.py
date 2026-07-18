import pytest

from valuez import (
    Categorical,
    Nominal,
    Ordinal,
    Qualitative,
    Reference,
    Scalar,
    Value,
    Vocabulary,
)


# --------------------------------------------------------------------------- #
# Vocabulary                                                                  #
# --------------------------------------------------------------------------- #
def test_vocabulary_membership_and_rank():
    v = Vocabulary("severity", ["low", "medium", "high"], ordered=True)
    assert v.contains("medium")
    assert not v.contains("nope")
    assert v.rank("low") == 0
    assert v.rank("high") == 2


def test_unordered_vocabulary_has_no_rank():
    v = Vocabulary("colour", ["red", "green", "blue"])
    with pytest.raises(ValueError):
        v.rank("red")


def test_vocabulary_validation():
    with pytest.raises(ValueError):
        Vocabulary("dup", ["a", "a"])
    with pytest.raises(ValueError):
        Vocabulary("empty", [])


def test_vocabulary_roundtrip():
    v = Vocabulary(
        "severity", ["low", "high"], ordered=True,
        definitions={"low": "minor", "high": "severe"},
        reference=Reference("ops-runbook", locator="sec.4"),
    )
    restored = Vocabulary.from_dict(v.to_dict())
    assert restored == v
    assert restored.reference == v.reference


# --------------------------------------------------------------------------- #
# Nominal                                                                     #
# --------------------------------------------------------------------------- #
def test_nominal_basic_and_grounding():
    ref = Reference("astm-a240", description="304 grade designation")
    n = Nominal("304", label="steel_grade", reference=ref)
    assert n.kind == "nominal"
    assert n.term == "304"
    assert n.is_grounded()
    assert not hasattr(n, "unit")  # qualitative values carry no unit


def test_nominal_validates_against_vocabulary():
    grades = Vocabulary("ss_grades", ["304", "316", "430"])
    assert Nominal("316", vocabulary=grades).term == "316"
    with pytest.raises(ValueError):
        Nominal("999", vocabulary=grades)


def test_nominal_roundtrip_embeds_vocabulary():
    grades = Vocabulary("ss_grades", ["304", "316"])
    n = Nominal("304", vocabulary=grades, id="g1", label="grade")
    restored = Value.from_dict(n.to_dict())
    assert isinstance(restored, Nominal)
    assert restored == n
    assert restored.vocabulary == grades


# --------------------------------------------------------------------------- #
# Ordinal                                                                     #
# --------------------------------------------------------------------------- #
SEVERITY = Vocabulary("severity", ["low", "medium", "high"], ordered=True)


def test_ordinal_requires_ordered_vocabulary():
    unordered = Vocabulary("colour", ["red", "blue"])
    with pytest.raises(ValueError):
        Ordinal("red", vocabulary=unordered)
    with pytest.raises(ValueError):
        Ordinal("low", vocabulary=None)  # type: ignore[arg-type]


def test_ordinal_rank_and_comparisons():
    low = Ordinal("low", vocabulary=SEVERITY)
    med = Ordinal("medium", vocabulary=SEVERITY)
    high = Ordinal("high", vocabulary=SEVERITY)
    assert low.rank == 0 and high.rank == 2
    assert low < med < high
    assert high > low
    assert low <= Ordinal("low", vocabulary=SEVERITY)
    assert sorted([high, low, med]) == [low, med, high]


def test_ordinal_cross_vocabulary_comparison_errors():
    other = Vocabulary("size", ["s", "m", "l"], ordered=True)
    with pytest.raises(ValueError):
        _ = Ordinal("low", vocabulary=SEVERITY) < Ordinal("m", vocabulary=other)


def test_ordinal_roundtrip():
    o = Ordinal("high", vocabulary=SEVERITY, id="sev1", label="risk")
    restored = Value.from_dict(o.to_dict())
    assert isinstance(restored, Ordinal)
    assert restored == o
    assert restored.rank == 2


# --------------------------------------------------------------------------- #
# Hierarchy / abstractness                                                    #
# --------------------------------------------------------------------------- #
def test_categorical_is_abstract():
    with pytest.raises(TypeError):
        Categorical("x")  # type: ignore[abstract]


def test_qualitative_and_quantitative_are_distinct_families():
    assert issubclass(Nominal, Qualitative)
    assert issubclass(Ordinal, Qualitative)
    # A numeric value is not qualitative.
    assert not isinstance(Scalar(1.0), Qualitative)
