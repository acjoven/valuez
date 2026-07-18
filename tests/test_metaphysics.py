import pytest

from valuez import (
    Individual,
    Instantiation,
    MetaphysicalEntity,
    Relation,
    Universal,
    Value,
    reasoning,
)


# --------------------------------------------------------------------------- #
# Individual / Universal                                                      #
# --------------------------------------------------------------------------- #
def test_individual_and_universal_kinds():
    soc = Individual("Socrates")
    human = Universal("Human")
    assert soc.kind == "individual"
    assert human.kind == "universal"
    assert soc.name == "Socrates" and human.name == "Human"


def test_metaphysical_entity_is_abstract():
    with pytest.raises(TypeError):
        MetaphysicalEntity("nope")


def test_ontological_status_optional_and_validated():
    assert Individual("x").ontological_status is None
    assert Individual("x", ontological_status="concrete").ontological_status == "concrete"
    with pytest.raises(ValueError):
        Universal("U", ontological_status="")
    with pytest.raises(ValueError):
        Universal("U", ontological_status=123)


def test_entity_roundtrip_preserves_status_and_type():
    for obj in (
        Individual("Socrates", ontological_status="concrete", id="i1"),
        Universal("Human", ontological_status="abstract", definition="rational animal", id="u1"),
    ):
        restored = Value.from_dict(obj.to_dict())
        assert type(restored) is type(obj)
        assert restored == obj
        assert restored.ontological_status == obj.ontological_status


# --------------------------------------------------------------------------- #
# Instantiation                                                               #
# --------------------------------------------------------------------------- #
def test_instantiation_fixes_predicate_and_direction():
    soc = Individual("Socrates")
    human = Universal("Human")
    inst = Instantiation(soc, human, modality="necessary")
    assert inst.kind == "instantiation"
    assert inst.predicate == "instantiates"
    assert inst.source == "Socrates" and inst.target == "Human"
    assert inst.modality == "necessary"


def test_instantiation_rejects_wrong_types():
    soc = Individual("Socrates")
    human = Universal("Human")
    with pytest.raises(TypeError):
        Instantiation(human, human)  # source must be an Individual
    with pytest.raises(TypeError):
        Instantiation(soc, soc)  # target must be a Universal


def test_instantiation_accepts_bare_names():
    inst = Instantiation("Socrates", "Human")
    assert inst.source == "Socrates" and inst.target == "Human"


def test_instantiation_roundtrip():
    inst = Instantiation(Individual("Plato"), Universal("Human"),
                         modality="necessary", strength=1.0, id="inst-1")
    restored = Value.from_dict(inst.to_dict())
    assert isinstance(restored, Instantiation)
    assert restored == inst
    assert restored.predicate == "instantiates"
    assert restored.modality == "necessary"


# --------------------------------------------------------------------------- #
# reasoning helper                                                            #
# --------------------------------------------------------------------------- #
def _chain(predicate):
    return [
        Relation("Cell", predicate, "Tissue"),
        Relation("Tissue", predicate, "Organ"),
        Relation("Organ", predicate, "Organism"),
    ]


def test_transitive_closure_pairs():
    closure = reasoning.transitive_closure(_chain("part-of"), "part-of")
    assert ("Cell", "Organism") in closure
    assert ("Cell", "Organ") in closure
    assert ("Tissue", "Organism") in closure
    assert ("Cell", "Cell") not in closure


def test_transitive_closure_ignores_other_predicates():
    rels = _chain("part-of") + [Relation("Cell", "is-a", "Thing")]
    closure = reasoning.transitive_closure(rels, "part-of")
    assert all(pred != "Thing" for _, pred in closure)


def test_infer_transitive_returns_new_inferred_edges():
    inferred = reasoning.infer_transitive(_chain("part-of"), "part-of")
    pairs = {(r.source, r.target) for r in inferred}
    assert pairs == {("Cell", "Organ"), ("Cell", "Organism"), ("Tissue", "Organism")}
    assert all(r.predicate == "part-of" for r in inferred)
    assert all(r.modality == "inferred" for r in inferred)


def test_is_acyclic_and_find_cycles():
    chain = _chain("grounds")
    assert reasoning.is_acyclic(chain, "grounds") is True
    assert reasoning.find_cycles(chain, "grounds") == []

    cyclic = chain + [Relation("Organism", "grounds", "Cell")]
    assert reasoning.is_acyclic(cyclic, "grounds") is False
    cycles = reasoning.find_cycles(cyclic, "grounds")
    assert len(cycles) == 1
    assert set(cycles[0]) == {"Cell", "Tissue", "Organ", "Organism"}
