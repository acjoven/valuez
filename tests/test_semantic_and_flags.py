import pytest

from valuez import (
    Boolean,
    Concept,
    Qualitative,
    Reference,
    Relation,
    Textual,
    Value,
    build_relation_graph,
    visualize_relations,
)


# --------------------------------------------------------------------------- #
# Boolean / Flag                                                              #
# --------------------------------------------------------------------------- #
def test_boolean_state_and_truthiness():
    b = Boolean(True, true_label="pass", false_label="fail", label="qc")
    assert b.state is True
    assert bool(b) is True
    assert b.term == "pass"
    assert Boolean(False, true_label="pass", false_label="fail").term == "fail"
    assert Boolean(False).term == "false"  # default labels


def test_boolean_rejects_non_bool():
    with pytest.raises(TypeError):
        Boolean(1)  # int is not bool
    with pytest.raises(TypeError):
        Boolean("yes")


def test_boolean_roundtrip():
    b = Boolean(True, true_label="present", false_label="absent", id="flag-1",
                reference=Reference("inspection-log"))
    restored = Value.from_dict(b.to_dict())
    assert isinstance(restored, Boolean)
    assert restored == b
    assert restored.state is True
    assert restored.term == "present"
    assert restored.is_grounded()


def test_boolean_has_no_unit():
    assert not hasattr(Boolean(True), "unit")
    assert isinstance(Boolean(True), Qualitative)


# --------------------------------------------------------------------------- #
# Textual                                                                     #
# --------------------------------------------------------------------------- #
def test_textual_basic_and_roundtrip():
    t = Textual("Surface shows mild pitting.", label="note", id="n1",
                reference=Reference("field-report#9"))
    assert t.text.startswith("Surface")
    restored = Value.from_dict(t.to_dict())
    assert isinstance(restored, Textual)
    assert restored == t
    assert restored.is_grounded()


def test_textual_rejects_non_string():
    with pytest.raises(TypeError):
        Textual(123)


# --------------------------------------------------------------------------- #
# Concept / Relation                                                          #
# --------------------------------------------------------------------------- #
def test_concept_roundtrip():
    c = Concept("Corrosion", definition="Degradation of metal by reaction with its environment.",
                id="c-corrosion", reference=Reference("materials-glossary"))
    restored = Value.from_dict(c.to_dict())
    assert isinstance(restored, Concept)
    assert restored == c
    assert restored.name == "Corrosion"
    assert restored.definition.startswith("Degradation")


def test_relation_accepts_concepts_or_strings():
    steel = Concept("StainlessSteel")
    metal = Concept("Metal")
    r1 = Relation(steel, "is-a", metal)
    r2 = Relation("StainlessSteel", "is-a", "Metal")
    assert r1.source == "StainlessSteel"
    assert r1.target == "Metal"
    assert r1.predicate == "is-a"
    assert r1.to_dict()["source"] == r2.to_dict()["source"]


def test_relation_requires_predicate():
    with pytest.raises(ValueError):
        Relation("A", "", "B")


def test_relation_roundtrip():
    r = Relation("StainlessSteel", "susceptible-to", "Corrosion", id="rel-1",
                 reference=Reference("ASM Handbook"))
    restored = Value.from_dict(r.to_dict())
    assert isinstance(restored, Relation)
    assert restored == r
    assert (restored.source, restored.predicate, restored.target) == (
        "StainlessSteel", "susceptible-to", "Corrosion")


# --------------------------------------------------------------------------- #
# Semantic graph                                                              #
# --------------------------------------------------------------------------- #
def test_build_relation_graph_structure():
    rels = [
        Relation("StainlessSteel", "is-a", "Metal"),
        Relation("StainlessSteel", "susceptible-to", "Corrosion"),
        Relation("Metal", "conducts", "Heat"),
    ]
    g = build_relation_graph(rels)
    assert g.number_of_nodes() == 4  # StainlessSteel, Metal, Corrosion, Heat
    assert g.number_of_edges() == 3
    assert g.has_edge("StainlessSteel", "Metal")
    assert g["StainlessSteel"]["Metal"]["label"] == "is-a"


def test_visualize_relations_writes_html(tmp_path, monkeypatch):
    # Run inside tmp_path so pyvis's vendored lib/ assets don't touch the repo.
    monkeypatch.chdir(tmp_path)
    rels = [Relation("A", "rel", "B")]
    out = visualize_relations(rels, tmp_path / "graph.html")
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip() != ""
