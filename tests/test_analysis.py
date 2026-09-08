"""Tests for valuez.analysis -- inference, tensions, gaps, Dung grounded status."""
import json
from pathlib import Path

import pytest

from valuez import (
    Analysis,
    Argument,
    Concept,
    Individual,
    Instantiation,
    Proposition,
    Reading,
    Reference,
    Relation,
    Universal,
    Vocabulary,
    analyze,
)
from valuez.metaphysics import Instantiation as Inst
from valuez.repository import ValueRepository

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _chain():
    return [
        Universal("Cell", definition="unit of life", id="n_cell", reference=Reference("SEP")),
        Universal("Tissue", definition="cells together", id="n_tissue", reference=Reference("SEP")),
        Universal("Organ", definition="tissues together", id="n_organ", reference=Reference("SEP")),
        Universal("Organism", definition="a living whole", id="n_org", reference=Reference("SEP")),
        Relation("Cell", "part-of", "Tissue", id="e1"),
        Relation("Tissue", "part-of", "Organ", id="e2"),
        Relation("Organ", "part-of", "Organism", id="e3"),
    ]


# --------------------------------------------------------------------------- #
# Inference                                                                   #
# --------------------------------------------------------------------------- #
def test_transitivity_emits_provenance_tagged_edges():
    report = analyze(_chain(), gaps=False, dung=False)
    pairs = {(d.relation.source, d.relation.target) for d in report.derived}
    assert pairs == {("Cell", "Organ"), ("Cell", "Organism"), ("Tissue", "Organism")}
    for d in report.derived:
        assert d.rule == "transitivity"
        assert d.relation.predicate == "part-of"
        assert d.relation.modality == "inferred"
        assert d.relation.reference is not None
        assert d.relation.reference.source == "valuez.analysis"
        assert d.relation.reference.metadata["rule"] == "transitivity"
        assert d.because == tuple(d.relation.reference.metadata["because"])
    cell_org = next(d for d in report.derived if d.relation.target == "Organism" and d.relation.source == "Cell")
    assert set(cell_org.because) == {"e1", "e2", "e3"}


def test_does_not_reemit_asserted_edges():
    rels = _chain() + [Relation("Cell", "part-of", "Organ", id="already")]
    report = analyze(rels, gaps=False, dung=False)
    pairs = {(d.relation.source, d.relation.target) for d in report.derived}
    assert ("Cell", "Organ") not in pairs
    assert ("Cell", "Organism") in pairs


def test_symmetry_of_contrasts_with():
    values = [
        Universal("Freedom", definition="x", id="n1", reference=Reference("K")),
        Universal("Nature", definition="y", id="n2", reference=Reference("K")),
        Relation("Freedom", "contrasts-with", "Nature", id="e1"),
    ]
    report = analyze(values, transitive=(), gaps=False, dung=False)
    assert len(report.derived) == 1
    d = report.derived[0]
    assert d.rule == "symmetry"
    assert (d.relation.source, d.relation.predicate, d.relation.target) == (
        "Nature", "contrasts-with", "Freedom",
    )
    assert d.because == ("e1",)


def test_instantiation_inheritance_along_is_a():
    values = [
        Individual("Socrates", id="i"),
        Universal("Human", definition="rational animal", id="u1"),
        Universal("Animal", definition="living", id="u2"),
        Universal("LivingThing", definition="kind", id="u3"),
        Instantiation("Socrates", "Human", id="inst"),
        Relation("Human", "is-a", "Animal", id="isa1"),
        Relation("Animal", "is-a", "LivingThing", id="isa2"),
    ]
    report = analyze(values, gaps=False, dung=False)
    inherited = [d for d in report.derived if d.rule == "instantiation-inheritance"]
    pairs = {(d.relation.source, d.relation.target) for d in inherited}
    assert pairs == {("Socrates", "Animal"), ("Socrates", "LivingThing")}
    assert all(isinstance(d.relation, Inst) for d in inherited)
    assert all(d.relation.predicate == "instantiates" for d in inherited)
    living = next(d for d in inherited if d.relation.target == "LivingThing")
    assert living.because[0] == "inst"
    assert "isa1" in living.because and "isa2" in living.because


def test_inherit_can_be_disabled():
    values = [
        Individual("Socrates", id="i"),
        Universal("Human", id="u1"),
        Universal("Animal", id="u2"),
        Instantiation("Socrates", "Human", id="inst"),
        Relation("Human", "is-a", "Animal", id="isa"),
    ]
    report = analyze(values, inherit_instantiation=False, gaps=False, dung=False)
    assert all(d.rule != "instantiation-inheritance" for d in report.derived)


# --------------------------------------------------------------------------- #
# Tensions                                                                    #
# --------------------------------------------------------------------------- #
def test_cycle_is_a_tension():
    rels = [
        Relation("A", "grounds", "B", id="e1"),
        Relation("B", "grounds", "C", id="e2"),
        Relation("C", "grounds", "A", id="e3"),
    ]
    report = analyze(rels, gaps=False, dung=False)
    kinds = [f.kind for f in report.tensions]
    assert "cycle" in kinds
    cycle = next(f for f in report.tensions if f.kind == "cycle")
    assert set(cycle.items) == {"A", "B", "C"}
    assert "grounds cycle" in cycle.detail


def test_clash_contrasts_with_is_a():
    values = [
        Universal("A", definition="a", id="n1"),
        Universal("B", definition="b", id="n2"),
        Relation("A", "contrasts-with", "B", id="c1"),
        Relation("A", "is-a", "B", id="i1"),
    ]
    report = analyze(values, gaps=False, dung=False, inherit_instantiation=False)
    clashes = [f for f in report.tensions if f.kind == "clash"]
    assert len(clashes) == 1
    assert "contrasts-with" in clashes[0].detail and "is-a" in clashes[0].detail
    assert {"c1", "i1"} <= set(clashes[0].items)


def test_clash_detects_inferred_is_a_against_contrast():
    values = [
        Universal("A", id="n1"),
        Universal("B", id="n2"),
        Universal("C", id="n3"),
        Relation("A", "contrasts-with", "C", id="c1"),
        Relation("A", "is-a", "B", id="i1"),
        Relation("B", "is-a", "C", id="i2"),
    ]
    report = analyze(values, gaps=False, dung=False)
    clashes = [f for f in report.tensions if f.kind == "clash"]
    assert clashes, "A contrasts-with C but inferred A is-a C"
    assert any(f.items and "c1" in f.items for f in clashes)


def test_proposition_truth_contradiction():
    values = [
        Proposition("The soul is simple.", truth_value=True, label="P", id="p1"),
        Proposition("The soul is simple.", truth_value=False, label="P-not", id="p2"),
    ]
    report = analyze(values, gaps=False, dung=False)
    contradictions = [f for f in report.tensions if f.kind == "contradiction"]
    assert len(contradictions) == 1
    assert set(contradictions[0].items) == {"p1", "p2"}


def test_tensions_can_be_disabled():
    rels = [Relation("A", "grounds", "B", id="e1"), Relation("B", "grounds", "A", id="e2")]
    report = analyze(rels, tensions=False, gaps=False, dung=False)
    assert report.tensions == ()


# --------------------------------------------------------------------------- #
# Gaps                                                                        #
# --------------------------------------------------------------------------- #
def test_gaps_dangling_isolated_undefined_ungrounded_open_missing():
    values = [
        Concept("Lonely", id="c1"),  # isolated, undefined, ungrounded
        Concept("Known", definition="has a def", id="c2", reference=Reference("S")),
        Relation("Known", "is-a", "Missing", id="e1"),  # dangling Missing
        Proposition("Is this true?", label="Q", id="q1"),  # open-question
        Argument(["Q", "NoSuch"], "AlsoMissing", label="Arg", id="a1"),
    ]
    report = analyze(values, tensions=False, dung=False, inherit_instantiation=False)
    kinds = {f.kind for f in report.gaps}
    assert kinds >= {"isolated", "undefined", "ungrounded", "dangling", "open-question", "missing-premise"}
    dangling = next(f for f in report.gaps if f.kind == "dangling")
    assert "Missing" in dangling.detail
    missing = next(f for f in report.gaps if f.kind == "missing-premise")
    assert "NoSuch" in missing.detail and "AlsoMissing" in missing.detail


def test_edge_citation_grounds_the_node():
    values = [
        Universal("A", definition="a", id="n1"),
        Universal("B", definition="b", id="n2"),
        Relation("A", "is-a", "B", id="e", reference=Reference("S")),
    ]
    report = analyze(values, tensions=False, dung=False)
    assert all(f.kind != "ungrounded" for f in report.gaps)


def test_relations_only_do_not_emit_dangling():
    report = analyze([Relation("A", "is-a", "B", id="e")], gaps=True, dung=False, tensions=False)
    assert all(f.kind != "dangling" for f in report.gaps)


# --------------------------------------------------------------------------- #
# Dung                                                                        #
# --------------------------------------------------------------------------- #
def test_dung_unattacked_is_accepted():
    args = [Argument(["P"], "C", label="Solo", id="a")]
    props = [Proposition("P", label="P", id="p"), Proposition("C", label="C", id="c")]
    report = analyze(args + props, gaps=False, tensions=False)
    assert report.arguments == {"Solo": "accepted"}


def test_dung_grounded_defeats_attacked_argument():
    values = [
        Proposition("p", label="P", id="p"),
        Proposition("c", label="C", id="c"),
        Proposition("q", label="Q", id="q"),
        Argument(["P"], "C", label="Gettier-Argument", id="g"),
        Argument(["Q"], "C", label="No-False-Lemmas", id="n"),
        Relation("No-False-Lemmas", "attacks", "Gettier-Argument", id="atk"),
    ]
    report = analyze(values, gaps=False, tensions=False)
    assert report.arguments["No-False-Lemmas"] == "accepted"
    assert report.arguments["Gettier-Argument"] == "defeated"


def test_dung_mutual_attack_is_undecided():
    values = [
        Proposition("p", label="P", id="p"),
        Proposition("c", label="C", id="c"),
        Argument(["P"], "C", label="A", id="a"),
        Argument(["P"], "C", label="B", id="b"),
        Relation("A", "attacks", "B", id="e1"),
        Relation("B", "attacks", "A", id="e2"),
    ]
    report = analyze(values, gaps=False, tensions=False)
    assert report.arguments == {"A": "undecided", "B": "undecided"}


def test_dung_ignores_attacks_on_concepts():
    values = [
        Concept("JustifiedTrueBelief", id="jtb"),
        Proposition("p", label="P", id="p"),
        Proposition("c", label="C", id="c"),
        Argument(["P"], "C", label="Gettier-Argument", id="g"),
        Relation("Gettier-Argument", "attacks", "JustifiedTrueBelief", id="atk"),
    ]
    report = analyze(values, gaps=False, tensions=False)
    assert report.arguments == {"Gettier-Argument": "accepted"}


# --------------------------------------------------------------------------- #
# Report shape / wrappers                                                     #
# --------------------------------------------------------------------------- #
def test_analysis_to_dict_and_summary():
    report = analyze(_chain(), dung=False)
    assert isinstance(report, Analysis)
    data = json.loads(json.dumps(report.to_dict()))
    assert len(data["derived"]) == 3
    assert "transitivity" in report.summary()
    assert report.relations[0].modality == "inferred"


def test_accepts_document_dicts():
    report = analyze([v.to_dict() for v in _chain()], gaps=False, dung=False)
    assert len(report.derived) == 3


def test_reading_analyze():
    book = Reading(source="T", predicates=Vocabulary("p", ["is-a", "part-of"]))
    with book.at("p.1"):
        book.universal("A", "a")
        book.universal("B", "b")
        book.universal("C", "c")
        book.relate("A", "is-a", "B")
        book.relate("B", "is-a", "C")
    report = book.analyze(gaps=False, dung=False)
    pairs = {(d.relation.source, d.relation.target) for d in report.derived}
    assert ("A", "C") in pairs


def test_repository_analyze(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    repo.add_values(_chain())
    report = repo.analyze(gaps=False, dung=False)
    assert len(report.derived) == 3


def test_kant_infers_is_a_and_is_acyclic():
    docs = json.loads((ONTOLOGIES / "kant.json").read_text(encoding="utf-8"))
    report = analyze(docs, dung=False)
    isa = [d for d in report.derived if d.relation.predicate == "is-a"]
    assert len(isa) > 0
    assert all(f.kind != "cycle" for f in report.tensions)
    # Category is-a Concept is-a Representation is asserted in the map via builders;
    # the inferred Category is-a Representation is the classic Stufenleiter hop.
    pairs = {(d.relation.source, d.relation.target) for d in isa}
    assert ("Category", "Representation") in pairs or any(
        d.relation.source == "Human" for d in isa
    )
