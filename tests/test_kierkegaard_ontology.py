"""Structural guards for examples/kierkegaard_ontology.py."""
import importlib.util
from pathlib import Path

from valuez import Individual, Instantiation, Universal, reasoning
from valuez.repository import ValueRepository


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent.parent / "examples" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


kierkegaard = _load("kierkegaard_ontology")


def _onto():
    return kierkegaard.build_ontology()


def test_referential_integrity():
    onto = _onto()
    assert kierkegaard.validate_integrity(onto) == []


def test_expected_population():
    onto = _onto()
    assert len(onto["individuals"]) == 22
    assert len(onto["universals"]) > 60
    assert len(onto["relations"]) > 150
    # every relation predicate is in the controlled vocabulary
    vocab = onto["vocabulary"]
    for r in onto["relations"]:
        assert vocab.contains(r.predicate)


def test_node_names_are_unique():
    onto = _onto()
    names = [c.name for c in onto["individuals"]] + [c.name for c in onto["universals"]]
    assert len(names) == len(set(names)), "individual/universal names must be unique"


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
    # the pseudonymous personae are typed as Pseudonyms; the works as works
    edges = {(inst.source, inst.target) for inst in onto["instantiations"]}
    assert ("JohannesClimacus", "Pseudonym") in edges
    assert ("FearAndTrembling", "PhilosophicalWork") in edges
    assert ("Abraham", "Exemplar") in edges


def test_strict_orders_are_acyclic():
    rels = _onto()["relations"]
    for pred in ("is-a", "part-of", "grounds"):
        assert reasoning.is_acyclic(rels, pred), f"{pred} must be acyclic"


def test_isa_transitive_closure_infers_expected_edges():
    rels = _onto()["relations"]
    pairs = reasoning.transitive_closure(rels, "is-a")
    # OriginalSin is-a Sin is-a TheologicalConcept  =>  OriginalSin is-a TheologicalConcept
    assert ("OriginalSin", "TheologicalConcept") in pairs
    # AbsoluteParadox is-a Paradox is-a TheologicalConcept
    assert ("AbsoluteParadox", "TheologicalConcept") in pairs
    # ReligiousnessB is-a ReligiousStage is-a StageOfExistence
    assert ("ReligiousnessB", "StageOfExistence") in pairs


def test_key_concepts_and_relations_present():
    onto = _onto()
    unames = {u.name for u in onto["universals"]}
    for name in ("Anxiety", "Despair", "Faith", "AbsoluteParadox", "TheSelf",
                 "Subjectivity", "TeleologicalSuspensionOfTheEthical", "AestheticStage"):
        assert name in unames
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    assert ("Subjectivity", "grounds", "Truth") in edges
    assert ("Faith", "requires", "TheAbsurd") in edges
    assert ("Freedom", "produces", "Anxiety") in edges
    assert ("Subjectivity", "contrasts-with", "Objectivity") in edges


def test_stage_progression_and_self_synthesis():
    onto = _onto()
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    # the three spheres of existence form a progression
    assert ("AestheticStage", "leads-to", "EthicalStage") in edges
    assert ("EthicalStage", "leads-to", "ReligiousStage") in edges
    # the self is a synthesis of the opposed determinations
    for term in ("Possibility", "Necessity", "Finitude", "Infinitude", "Temporality", "Eternity"):
        assert ("TheSelf", "synthesizes", term) in edges
        assert (term, "part-of", "Synthesis") in edges


def test_authorship_and_exemplars():
    onto = _onto()
    edges = {(r.source, r.predicate, r.target) for r in onto["relations"]}
    # Kierkegaard wrote under his personae, who in turn wrote the pseudonymous works
    assert ("SorenKierkegaard", "authored-as", "JohannesDeSilentio") in edges
    assert ("JohannesDeSilentio", "wrote", "FearAndTrembling") in edges
    # Abraham exemplifies the knight of faith
    assert ("Abraham", "exemplifies", "KnightOfFaith") in edges
    # the authorship's critique targets
    assert ("SorenKierkegaard", "critiques", "Christendom") in edges


def test_arguments_present():
    onto = _onto()
    labels = {a.handle for a in onto["arguments"]}
    assert {"Teleological-Suspension", "Subjectivity-Is-Truth", "Self-And-Despair",
            "Against-The-System", "Paradox-And-Offense"} <= labels


def test_merge_anchors_overlap_with_kant():
    """The whole point of a second ontology: shared *names* for a future merge.

    The declared MERGE_ANCHORS must actually be present in *both* ontologies, and
    the two files must not collide by *id* (so a merge is forced to key on name).
    """
    kant = _load("kant_ontology")
    k_onto, s_onto = kant.build_ontology(), _onto()
    k_names = {u.name for u in k_onto["universals"]}
    s_names = {u.name for u in s_onto["universals"]}
    shared = k_names & s_names
    assert set(kierkegaard.MERGE_ANCHORS) <= shared
    # clean matches and genuine semantic collisions are both represented
    assert {"Philosopher", "PhilosophicalWork"} <= shared          # clean
    assert {"Existence", "Freedom", "God"} <= shared               # collisions
    # ids are disjoint across the two files (kk_ vs k_ prefixes)
    k_ids = {v.id for v in k_onto["universals"]}
    s_ids = {v.id for v in s_onto["universals"]}
    assert k_ids.isdisjoint(s_ids)


def test_semantic_collision_definitions_differ():
    """A collision anchor should carry *different* content in the two files.

    This is exactly the case a merge must resolve (same name, different meaning).
    """
    kant = _load("kant_ontology")
    k_by_name = {u.name: u for u in kant.build_ontology()["universals"]}
    s_by_name = {u.name: u for u in _onto()["universals"]}
    ex_k, ex_s = k_by_name["Existence"], s_by_name["Existence"]
    assert ex_k.definition != ex_s.definition
    # Kant files 'Existence' as an a priori category of modality; here it is existential
    assert ex_k.ontological_status != ex_s.ontological_status


def test_ontology_roundtrips_through_repository(tmp_path):
    onto = _onto()
    everything = (onto["individuals"] + onto["universals"] + onto["relations"]
                  + onto["instantiations"] + onto["propositions"] + onto["arguments"])
    repo = ValueRepository(data_dir=tmp_path / "store")
    repo.add_values(everything)

    path = repo.export_ontology(tmp_path / "kierkegaard.json")
    reloaded = ValueRepository.from_ontology(path, data_dir=tmp_path / "store2")
    assert len(reloaded.query("[]")) == len(everything)
    sk = reloaded.get_value("kk_sorenkierkegaard")
    assert isinstance(sk, Individual)
    despair = reloaded.get_value("kk_despair")
    assert isinstance(despair, Universal) and despair.ontological_status == "psychological"


def test_committed_canonical_matches_builder():
    """The committed ontologies/kierkegaard.json matches what the builder emits."""
    import json

    onto = _onto()
    expected = (len(onto["individuals"]) + len(onto["universals"]) + len(onto["relations"])
                + len(onto["instantiations"]) + len(onto["propositions"]) + len(onto["arguments"]))
    canonical = Path(__file__).resolve().parent.parent / "ontologies" / "kierkegaard.json"
    docs = json.loads(canonical.read_text())
    assert isinstance(docs, list) and len(docs) == expected
