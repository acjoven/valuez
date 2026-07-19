"""Structural guards for examples/kant_ontology.py."""
import importlib.util
from pathlib import Path

from valuez import Individual, Instantiation, Relation, Universal, Value, reasoning
from valuez.repository import ValueRepository

_SPEC = importlib.util.spec_from_file_location(
    "kant_ontology",
    Path(__file__).resolve().parent.parent / "examples" / "kant_ontology.py",
)
kant = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(kant)


def _onto():
    return kant.build_ontology()


def test_referential_integrity():
    onto = _onto()
    assert kant.validate_integrity(onto) == []


def test_expected_population():
    onto = _onto()
    assert len(onto["individuals"]) == 6
    assert len(onto["universals"]) > 60
    # every relation predicate is in the controlled vocabulary
    vocab = onto["vocabulary"]
    for r in onto["relations"]:
        assert vocab.contains(r.predicate)


def test_instantiation_typing_is_individual_to_universal():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    inames = {i.name for i in onto["individuals"]}
    assert onto["instantiations"], "expected instantiation edges"
    for inst in onto["instantiations"]:
        assert isinstance(inst, Instantiation)
        assert inst.predicate == "instantiates"
        assert inst.source in inames
        assert inst.target in unames


def test_strict_orders_are_acyclic():
    rels = _onto()["relations"]
    for pred in ("is-a", "part-of", "grounds"):
        assert reasoning.is_acyclic(rels, pred), f"{pred} must be acyclic"


def test_isa_transitive_closure_infers_expected_edges():
    rels = _onto()["relations"]
    pairs = reasoning.transitive_closure(rels, "is-a")
    # Category is-a Concept is-a Representation  =>  Category is-a Representation
    assert ("Category", "Representation") in pairs
    # Unity is-a CategoriesOfQuantity is-a Category  =>  Unity is-a Category
    assert ("Unity", "Category") in pairs
    assert ("Substance", "Representation") in pairs


def test_key_concepts_and_relations_present():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    for name in ("SyntheticAPriori", "CategoricalImperative", "ThingInItself",
                 "TranscendentalDeduction", "Beautiful", "Autonomy"):
        assert name in unames
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    assert ("Appearance", "contrasts-with", "ThingInItself") in edges
    assert ("Cognition", "requires", "Intuition") in edges
    assert ("CategoricalImperative", "requires", "Universalizability") in edges


def test_extension_ci_formulas():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    formulas = {"FormulaOfUniversalLaw", "FormulaOfHumanity",
                "FormulaOfAutonomy", "FormulaOfKingdomOfEnds"}
    assert formulas <= unames
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    for f in formulas:
        assert (f, "formulation-of", "CategoricalImperative") in edges
    # each formula is subsumed under the categorical imperative
    pairs = reasoning.transitive_closure(onto["relations"], "is-a")
    assert ("FormulaOfHumanity", "MoralConcept") in pairs


def test_extension_antinomies_and_paralogisms():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    antinomies = {"FirstAntinomy", "SecondAntinomy", "ThirdAntinomy", "FourthAntinomy"}
    paralogisms = {"ParalogismOfSubstantiality", "ParalogismOfSimplicity",
                   "ParalogismOfPersonality", "ParalogismOfIdeality"}
    assert antinomies <= unames and paralogisms <= unames
    pairs = reasoning.transitive_closure(onto["relations"], "is-a")
    for a in antinomies:
        assert (a, "Antinomy") in pairs
    for p in paralogisms:
        assert (p, "Paralogism") in pairs
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    assert ("ThirdAntinomy", "addresses", "Freedom") in edges


def test_extension_postulates_and_arguments():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    assert {"Postulate", "HighestGood", "ImmortalityOfSoul", "ExistenceOfGod"} <= unames
    pairs = reasoning.transitive_closure(onto["relations"], "is-a")
    assert ("ImmortalityOfSoul", "MoralConcept") in pairs  # Postulate is-a MoralConcept
    labels = {a.handle for a in onto["arguments"]}
    assert {"Transcendental-Deduction", "Good-Will-Argument",
            "Third-Antinomy-Resolution", "Postulates-Argument"} <= labels


def test_ontology_roundtrips_through_repository(tmp_path):
    onto = _onto()
    everything = (onto["individuals"] + onto["universals"] + onto["relations"]
                  + onto["instantiations"] + onto["propositions"] + onto["arguments"])
    repo = ValueRepository(data_dir=tmp_path / "store")
    repo.add_values(everything)

    path = repo.export_ontology(tmp_path / "kant.json")
    reloaded = ValueRepository.from_ontology(path, data_dir=tmp_path / "store2")
    assert len(reloaded.query("[]")) == len(everything)
    kant_ind = reloaded.get_value("k_immanuelkant")
    assert isinstance(kant_ind, Individual)
    # a rehydrated universal keeps its ontological_status
    tii = reloaded.get_value("k_thinginitself")
    assert isinstance(tii, Universal) and tii.ontological_status == "noumenal"
