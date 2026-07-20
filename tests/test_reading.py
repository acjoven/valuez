"""Tests for the fluent authoring layer (valuez.reading.Reading)."""
import json

import pytest

from valuez import (
    Concept,
    Individual,
    Instantiation,
    OntologyBuilder,
    Proposition,
    Reading,
    Relation,
    Universal,
    Value,
    Vocabulary,
)
from valuez.repository import ValueRepository


def _preds() -> Vocabulary:
    return Vocabulary("preds", ["is-a", "part-of", "grounds", "instantiates", "wrote"])


# --------------------------------------------------------------------------- #
# Citation context + reference propagation                                    #
# --------------------------------------------------------------------------- #
def test_at_propagates_reference_to_all_items():
    r = Reading(source="Critique of Pure Reason")
    with r.at("A51/B75", confidence=0.9):
        u = r.universal("Understanding", "faculty of concepts")
        p = r.claim("Thoughts without content are empty.", truth_value=True)
    assert u.reference is not None
    assert u.reference.source == "Critique of Pure Reason"
    assert u.reference.locator == "A51/B75"
    assert u.reference.confidence == 0.9
    assert p.reference is not None and p.reference.locator == "A51/B75"


def test_items_outside_context_are_ungrounded():
    r = Reading(source="Some Text")
    u = r.universal("Freedom")
    assert u.reference is None and not u.is_grounded()


def test_nested_context_innermost_wins_and_pops():
    r = Reading(source="T")
    with r.at("ch.1"):
        a = r.universal("A")
        with r.at("ch.2"):
            b = r.universal("B")
        c = r.universal("C")
    assert a.reference.locator == "ch.1"
    assert b.reference.locator == "ch.2"
    assert c.reference.locator == "ch.1"  # popped back to outer context


def test_each_item_gets_independent_reference_clone():
    r = Reading(source="T")
    with r.at("p1"):
        a = r.universal("A")
        b = r.universal("B")
    assert a.reference is not b.reference
    a.reference.metadata["x"] = 1
    assert "x" not in b.reference.metadata


def test_at_without_source_raises():
    r = Reading()  # no session source
    with pytest.raises(ValueError):
        with r.at("somewhere"):
            pass
    # ... but an explicit per-block source works
    with r.at("somewhere", source="Quoted Text"):
        u = r.universal("Thing")
    assert u.reference.source == "Quoted Text"


def test_cite_pushes_explicit_reference():
    from valuez import Reference

    r = Reading(source="Primary")
    with r.cite(Reference("Secondary", locator="fn.3")):
        u = r.concept("Gloss")
    assert u.reference.source == "Secondary" and u.reference.locator == "fn.3"


# --------------------------------------------------------------------------- #
# Concept create-or-reuse (dedup + enrichment + conflicts)                    #
# --------------------------------------------------------------------------- #
def test_concept_dedup_returns_same_node():
    r = Reading(source="T")
    a = r.universal("Reason")
    b = r.universal("Reason")
    assert a is b
    assert len(r.universals) == 1


def test_dedup_enriches_missing_definition():
    r = Reading(source="T")
    a = r.universal("Reason")
    assert a.definition is None
    b = r.universal("Reason", "faculty of principles")
    assert a is b and a.definition == "faculty of principles"


def test_conflicting_definition_raises():
    r = Reading(source="T")
    r.universal("Reason", "def one")
    with pytest.raises(ValueError):
        r.universal("Reason", "a different def")


def test_type_conflict_raises():
    r = Reading(source="T")
    r.universal("Freedom")
    with pytest.raises(ValueError):
        r.individual("Freedom")  # already a Universal


def test_factory_types_and_status():
    r = Reading(source="T")
    ind = r.individual("Kant", ontological_status="historical")
    uni = r.universal("Philosopher", ontological_status="abstract")
    con = r.concept("Note")
    assert isinstance(ind, Individual) and ind.ontological_status == "historical"
    assert isinstance(uni, Universal) and uni.ontological_status == "abstract"
    assert type(con) is Concept


# --------------------------------------------------------------------------- #
# Relations: eager validation                                                 #
# --------------------------------------------------------------------------- #
def test_relate_unknown_endpoint_raises_immediately():
    r = Reading(source="T")
    r.universal("A")
    with pytest.raises(ValueError):
        r.relate("A", "is-a", "B")  # B not declared


def test_relate_predicate_vocabulary_enforced():
    r = Reading(source="T", predicates=_preds())
    r.universal("A")
    r.universal("B")
    with pytest.raises(ValueError):
        r.relate("A", "not-a-predicate", "B")
    rel = r.relate("A", "is-a", "B")
    assert isinstance(rel, Relation) and rel.predicate == "is-a"


def test_relate_accepts_concept_objects_and_autodeclares():
    r = Reading(source="T")
    a = r.universal("A")
    b = Universal("B")  # constructed outside the session
    rel = r.relate(a, "grounds", b)
    assert rel.source == "A" and rel.target == "B"
    assert r.has("B")  # auto-declared by passing the object


def test_relate_attaches_context_reference():
    r = Reading(source="T")
    r.universal("A")
    r.universal("B")
    with r.at("p.10"):
        rel = r.relate("A", "grounds", "B")
    assert rel.reference.locator == "p.10"


# --------------------------------------------------------------------------- #
# Instantiation typing                                                        #
# --------------------------------------------------------------------------- #
def test_instantiate_enforces_individual_to_universal():
    r = Reading(source="T")
    r.individual("Socrates")
    r.universal("Human")
    inst = r.instantiate("Socrates", "Human")
    assert isinstance(inst, Instantiation)
    assert inst.predicate == "instantiates"
    assert inst in r.instantiations


def test_instantiate_wrong_direction_raises():
    r = Reading(source="T")
    r.universal("Human")
    r.individual("Socrates")
    with pytest.raises(TypeError):
        r.instantiate("Human", "Socrates")  # Universal cannot instantiate


def test_relate_routes_instantiates_to_typed_edge():
    r = Reading(source="T")
    r.individual("Socrates")
    r.universal("Human")
    edge = r.relate("Socrates", "instantiates", "Human")
    assert isinstance(edge, Instantiation)


# --------------------------------------------------------------------------- #
# Propositions & arguments                                                    #
# --------------------------------------------------------------------------- #
def test_claim_dedup_by_handle_and_enrichment():
    r = Reading(source="T")
    p = r.claim("Space is a priori.", label="P-Space")
    assert p.truth_value is None
    p2 = r.claim("Space is a priori.", truth_value=True, label="P-Space")
    assert p is p2 and p.truth_value is True


def test_claim_handle_conflict_raises():
    r = Reading(source="T")
    r.claim("Statement one.", label="P")
    with pytest.raises(ValueError):
        r.claim("A different statement.", label="P")


def test_argue_with_objects_and_handles():
    r = Reading(source="T")
    pr = r.claim("All men are mortal.", label="P1")
    r.claim("Socrates is a man.", label="P2")
    arg = r.argue([pr, "P2"], "Socrates is mortal.", scheme="syllogism", label="A1")
    assert arg.premises == ["P1", "P2"]
    assert arg.conclusion == "Socrates is mortal."
    assert arg in r.arguments


# --------------------------------------------------------------------------- #
# Ids, stats, validation, reasoning                                           #
# --------------------------------------------------------------------------- #
def test_ids_are_prefixed_and_unique():
    r = Reading(source="T", id_prefix="k_")
    a = r.universal("Pure Reason")
    b = r.universal("Understanding")
    assert a.id == "k_pure_reason"
    r.relate(a, "grounds", b)
    ids = [v.id for v in r.values()]
    assert len(ids) == len(set(ids))  # all unique
    assert all(i.startswith("k_") for i in ids)


def test_stats_and_len():
    r = Reading(source="T")
    r.universal("A")
    r.universal("B")
    r.relate("A", "is-a", "B")
    r.claim("A is a B.")
    s = r.stats()
    assert s == {
        "concepts": 2, "individuals": 0, "universals": 2, "relations": 1,
        "instantiations": 0, "propositions": 1, "arguments": 0,
    }
    assert len(r) == 4


def test_validate_clean_and_check_returns_self():
    r = Reading(source="T")
    r.universal("A")
    r.universal("B")
    r.relate("A", "is-a", "B")
    assert r.validate() == []
    assert r.check() is r


def test_reasoning_helpers_delegate():
    r = Reading(source="T", predicates=_preds())
    for n in ("A", "B", "C"):
        r.universal(n)
    r.relate("A", "is-a", "B")
    r.relate("B", "is-a", "C")
    assert r.is_acyclic("is-a") is True
    inferred = r.infer_transitive("is-a")
    assert [(e.source, e.target) for e in inferred] == [("A", "C")]
    assert all(e.modality == "inferred" for e in inferred)


# --------------------------------------------------------------------------- #
# Persistence & round-trip                                                    #
# --------------------------------------------------------------------------- #
def _sample_session() -> Reading:
    r = Reading(source="Critique of Pure Reason", predicates=_preds(), id_prefix="k_")
    with r.at("Preface"):
        r.individual("ImmanuelKant", "author", ontological_status="historical")
        r.universal("Philosopher")
        r.instantiate("ImmanuelKant", "Philosopher")
    with r.at("A51/B75"):
        r.universal("Intuition")
        r.universal("Concept")
        r.universal("Cognition")
        r.relate("Cognition", "grounds", "Intuition")
        r.relate("Cognition", "grounds", "Concept")
        r.claim("Thoughts without content are empty.", truth_value=True, label="P-Empty")
    return r


def test_export_is_deterministic(tmp_path):
    p1 = _sample_session().export(tmp_path / "a.json", data_dir=tmp_path / "sa")
    p2 = _sample_session().export(tmp_path / "b.json", data_dir=tmp_path / "sb")
    assert p1.read_text() == p2.read_text()
    docs = json.loads(p1.read_text())
    assert len(docs) == len(_sample_session().values())
    # sorted by id, deterministic keys
    ids = [d["id"] for d in docs]
    assert ids == sorted(ids)


def test_roundtrip_through_repository(tmp_path):
    r = _sample_session()
    path = r.export(tmp_path / "o.json", data_dir=tmp_path / "store")
    repo = ValueRepository.from_ontology(path, data_dir=tmp_path / "reload")
    kinds = {row["kind"] for row in repo.query("[*]")}
    assert kinds == {"individual", "universal", "instantiation", "relation", "proposition"}
    kant = repo.get_value("k_immanuelkant")
    assert isinstance(kant, Individual) and kant.name == "ImmanuelKant"


def test_to_repository_contains_everything(tmp_path):
    r = _sample_session()
    repo = r.to_repository(data_dir=tmp_path / "store")
    stored = repo.query("[*].id")
    assert set(stored) == {v.id for v in r.values()}


# --------------------------------------------------------------------------- #
# Alias                                                                       #
# --------------------------------------------------------------------------- #
def test_ontology_builder_is_reading():
    assert OntologyBuilder is Reading
    b = OntologyBuilder(source="T")
    assert isinstance(b, Reading)
