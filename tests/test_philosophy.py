import pytest

from valuez import (
    Argument,
    Proposition,
    Relation,
    Value,
    Vocabulary,
    build_argument_graph,
    visualize_arguments,
)

PREDICATES = Vocabulary(
    "philosophical_relations",
    ["entails", "contradicts", "presupposes", "supports", "attacks", "defines"],
)


# --------------------------------------------------------------------------- #
# Relation: predicate vocabulary + qualifiers                                 #
# --------------------------------------------------------------------------- #
def test_relation_predicate_vocabulary_validates():
    r = Relation("JTB", "defines", "Knowledge", vocabulary=PREDICATES)
    assert r.predicate == "defines"
    with pytest.raises(ValueError):
        Relation("A", "vibes-with", "B", vocabulary=PREDICATES)


def test_relation_modality_and_strength():
    r = Relation("JTB", "presupposes", "Justification", modality="necessary", strength=0.8)
    assert r.modality == "necessary"
    assert r.strength == 0.8
    with pytest.raises(ValueError):
        Relation("A", "entails", "B", strength=1.5)
    with pytest.raises(TypeError):
        Relation("A", "entails", "B", strength=True)


def test_relation_qualifiers_roundtrip():
    r = Relation("Gettier", "attacks", "JTB", vocabulary=PREDICATES,
                 modality="defeasible", strength=0.9, id="rel-1")
    restored = Value.from_dict(r.to_dict())
    assert isinstance(restored, Relation)
    assert restored == r
    assert restored.modality == "defeasible"
    assert restored.strength == 0.9
    assert restored.vocabulary == PREDICATES


# --------------------------------------------------------------------------- #
# Proposition                                                                 #
# --------------------------------------------------------------------------- #
def test_proposition_truth_value_and_handle():
    p = Proposition("Knowledge is justified true belief.", truth_value=False,
                    label="P1")
    assert p.truth_value is False
    assert p.handle == "P1"
    assert Proposition("bare claim").handle == "bare claim"
    with pytest.raises(TypeError):
        Proposition("x", truth_value="no")


def test_proposition_roundtrip():
    p = Proposition("Gettier cases are JTB but not knowledge.", truth_value=True,
                    id="p2", label="P2")
    restored = Value.from_dict(p.to_dict())
    assert isinstance(restored, Proposition)
    assert restored == p
    assert restored.truth_value is True


# --------------------------------------------------------------------------- #
# Argument                                                                    #
# --------------------------------------------------------------------------- #
def test_argument_from_propositions_or_handles():
    p1 = Proposition("Knowledge is JTB.", label="P1")
    p2 = Proposition("Gettier cases are JTB but not knowledge.", label="P2")
    arg = Argument([p1, p2], "JTB is insufficient for knowledge.",
                   scheme="reductio", label="Gettier")
    assert arg.premises == ["P1", "P2"]
    assert arg.conclusion == "JTB is insufficient for knowledge."
    assert arg.scheme == "reductio"
    assert arg.handle == "Gettier"


def test_argument_requires_premises():
    with pytest.raises(ValueError):
        Argument([], "c")


def test_argument_roundtrip():
    arg = Argument(["P1", "P2"], "C", scheme="modus-ponens", id="arg-1", label="A1")
    restored = Value.from_dict(arg.to_dict())
    assert isinstance(restored, Argument)
    assert restored == arg
    assert restored.premises == ["P1", "P2"]


# --------------------------------------------------------------------------- #
# Argument graph                                                              #
# --------------------------------------------------------------------------- #
def test_build_argument_graph_wires_premises_and_conclusion():
    arg = Argument(["P1", "P2"], "C", label="A1")
    g = build_argument_graph([arg])
    assert g.has_edge("P1", "A1") and g["P1"]["A1"]["label"] == "premise"
    assert g.has_edge("A1", "C") and g["A1"]["C"]["label"] == "concludes"


def test_build_argument_graph_overlays_relations():
    arg = Argument(["P1"], "C", label="A1")
    rel = Relation("A2", "attacks", "A1")
    g = build_argument_graph([arg], relations=[rel])
    assert g.has_edge("A2", "A1")
    assert g["A2"]["A1"]["label"] == "attacks"


def test_visualize_arguments_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # keep pyvis lib/ out of the repo
    arg = Argument(["P1", "P2"], "C", label="A1")
    out = visualize_arguments([arg], tmp_path / "args.html")
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip() != ""
