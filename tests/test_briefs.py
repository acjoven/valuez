"""Tests for valuez.briefs -- readable concept briefs via explain(node)."""
import json
from pathlib import Path

import pytest

from valuez import (
    Argument,
    Brief,
    Concept,
    Proposition,
    Reading,
    Reference,
    Relation,
    Universal,
    Vocabulary,
    explain,
    merge_ontologies,
)
from valuez.repository import ValueRepository

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"

PLATO = Reference("Plato, Theaetetus", locator="201c")
GETTIER = Reference("Gettier (1963)", locator="p. 121")


def _framework():
    """The Gettier mini-framework: concepts, edges, claims, an edge-linked argument."""
    concepts = [
        Concept("Knowledge", definition="Cognitive success.", id="c_k", reference=PLATO),
        Concept("JustifiedTrueBelief", definition="Belief that is true and justified.",
                id="c_jtb", reference=PLATO),
        Concept("Belief", id="c_b"),
        Concept("Justification", definition="What entitles a belief.", id="c_j"),
        Concept("Unrelated", definition="Nothing to do with knowledge here.", id="c_u"),
    ]
    rels = [
        Relation("JustifiedTrueBelief", "defines", "Knowledge", modality="proposed",
                 strength=0.6, id="r_def", reference=PLATO),
        Relation("JustifiedTrueBelief", "presupposes", "Belief", modality="necessary",
                 id="r_bel"),
        Relation("JustifiedTrueBelief", "presupposes", "Justification", id="r_jus"),
    ]
    props = [
        Proposition("Knowledge is justified true belief.", label="P1", id="p1", reference=PLATO),
        Proposition("In Gettier cases a subject has a JTB that is not knowledge.",
                    truth_value=True, label="P2", id="p2", reference=GETTIER),
        Proposition("Justified true belief is not sufficient for knowledge.",
                    truth_value=True, label="C", id="pc", reference=GETTIER),
        Proposition("Water is wet.", truth_value=True, label="Off", id="p_off"),
    ]
    gettier = Argument(["P1", "P2"], "C", scheme="reductio", label="Gettier-Argument",
                       id="arg_g", reference=GETTIER)
    attack = Relation("Gettier-Argument", "attacks", "JustifiedTrueBelief",
                      modality="defeasible", strength=0.9, id="r_att", reference=GETTIER)
    return concepts + rels + props + [gettier, attack]


# --------------------------------------------------------------------------- #
# Node, relations, neighbors                                                  #
# --------------------------------------------------------------------------- #
def test_node_fields_are_surfaced():
    b = explain(_framework(), "JustifiedTrueBelief")
    assert isinstance(b, Brief)
    assert b.kind == "concept"
    assert b.definition == "Belief that is true and justified."
    assert b.ontological_status is None
    assert b.node.id == "c_jtb"


def test_outgoing_and_incoming_are_separated_and_sorted():
    b = explain(_framework(), "JustifiedTrueBelief")
    assert [(r.predicate, r.target) for r in b.outgoing] == [
        ("defines", "Knowledge"),
        ("presupposes", "Belief"),
        ("presupposes", "Justification"),
    ]
    assert [(r.source, r.predicate) for r in b.incoming] == [("Gettier-Argument", "attacks")]
    assert b.by_predicate("out") == {
        "defines": ["Knowledge"],
        "presupposes": ["Belief", "Justification"],
    }
    assert b.by_predicate("in") == {"attacks": ["Gettier-Argument"]}


def test_neighbors_exclude_self_and_dedupe():
    b = explain(_framework(), "JustifiedTrueBelief")
    assert b.neighbors == ("Belief", "Gettier-Argument", "Justification", "Knowledge")


def test_unknown_node_raises():
    with pytest.raises(ValueError, match="unknown node"):
        explain(_framework(), "NoSuch")


def test_accepts_concept_object_and_document_dicts():
    docs = [v.to_dict() for v in _framework()]
    b = explain(docs, Concept("Knowledge"))
    assert b.name == "Knowledge"
    assert [r.source for r in b.incoming] == ["JustifiedTrueBelief"]


def test_edge_endpoint_without_node_doc_still_explains():
    rels = [Relation("A", "is-a", "B", id="r")]
    b = explain(rels, "B")
    assert b.node is None and b.kind is None
    assert [r.source for r in b.incoming] == ["A"]
    assert not b.is_empty()


# --------------------------------------------------------------------------- #
# Claims and arguments: edge-linked vs mention                                #
# --------------------------------------------------------------------------- #
def test_edge_linked_argument_is_marked_edge():
    b = explain(_framework(), "JustifiedTrueBelief")
    hows = {a.handle: how for a, how in b.arguments}
    assert hows == {"Gettier-Argument": "edge"}


def test_mentions_are_found_and_labelled():
    b = explain(_framework(), "Knowledge")
    claims = {p.label: how for p, how in b.propositions}
    # P1, P2, C all say "knowledge"; "Off" does not.
    assert claims == {"P1": "mention", "P2": "mention", "C": "mention"}
    # The argument's premises/conclusion are bare handles (P1/P2/C), not prose,
    # and its attack edge touches JTB, not Knowledge -> no argument surfaces.
    assert b.arguments == ()

def test_mentions_can_be_disabled():
    b = explain(_framework(), "Knowledge", mentions=False)
    assert b.propositions == ()
    assert b.arguments == ()
    assert b.mentioned_in == ()


def test_mentioned_in_definitions_uses_word_boundaries():
    values = [
        Universal("Law", definition="A rule.", id="u1"),
        Universal("Lawful", definition="Conforming to law.", id="u2"),
        Universal("Outlaw", definition="Beyond the lawgiver.", id="u3"),
        Universal("MoralLaw", definition="The moral law binds the will.", id="u4"),
        Relation("MoralLaw", "is-a", "Law", id="r"),
    ]
    b = explain(values, "Law")
    # 'Lawful' says "law" as a whole word; 'Outlaw' only "lawgiver" -> no hit.
    assert [c.name for c in b.mentioned_in] == ["Lawful", "MoralLaw"]


def test_camel_case_name_matches_prose():
    values = [
        Universal("MoralLaw", id="u1"),
        Universal("Autonomy", id="u2"),
        Relation("Autonomy", "grounds", "MoralLaw", id="r"),
        Proposition("The moral law is given by autonomy.", label="P", id="p"),
    ]
    b = explain(values, "MoralLaw")
    assert [(p.label, how) for p, how in b.propositions] == [("P", "mention")]


def test_argument_text_mentions_are_found():
    values = [
        Universal("Freedom", id="u1"),
        Universal("Nature", id="u2"),
        Relation("Freedom", "contrasts-with", "Nature", id="r"),
        Argument(["Freedom is a postulate.", "Nature is lawful."],
                 "Freedom and nature coexist.", label="Arg", id="a"),
    ]
    b = explain(values, "Freedom")
    assert [(a.handle, how) for a, how in b.arguments] == [("Arg", "mention")]


# --------------------------------------------------------------------------- #
# Citations                                                                   #
# --------------------------------------------------------------------------- #
def test_citations_are_deduplicated_node_first():
    b = explain(_framework(), "JustifiedTrueBelief")
    cites = b.citations()
    assert cites[0] == PLATO
    assert cites.count(PLATO) == 1
    assert GETTIER in cites


def test_sources_group_locators():
    b = explain(_framework(), "JustifiedTrueBelief")
    assert b.sources() == {
        "Gettier (1963)": ["p. 121"],
        "Plato, Theaetetus": ["201c"],
    }


def test_bibliography_includes_unkeyed_by_default():
    b = explain(_framework(), "JustifiedTrueBelief")
    bib = b.bibliography()
    assert len(bib) == 2
    assert len(b.bibliography(include_unkeyed=False)) == 0


# --------------------------------------------------------------------------- #
# Rendering                                                                   #
# --------------------------------------------------------------------------- #
def test_to_dict_is_json_serializable_and_complete():
    b = explain(_framework(), "JustifiedTrueBelief")
    data = json.loads(json.dumps(b.to_dict()))
    assert data["name"] == "JustifiedTrueBelief"
    assert data["kind"] == "concept"
    assert [r["target"] for r in data["outgoing"]] == ["Knowledge", "Belief", "Justification"]
    assert data["arguments"][0]["how"] == "edge"
    assert data["sources"]["Plato, Theaetetus"] == ["201c"]


def test_markdown_sections():
    md = explain(_framework(), "JustifiedTrueBelief").to_markdown()
    assert md.startswith("# JustifiedTrueBelief\n*concept*\n")
    assert "Belief that is true and justified." in md
    assert "## Relations" in md
    assert "- JustifiedTrueBelief —defines [proposed] (0.6)→ Knowledge  (Plato, Theaetetus, 201c)" in md
    assert "- Gettier-Argument —attacks [defeasible] (0.9)→ JustifiedTrueBelief" in md
    assert "## Arguments" in md and "**Gettier-Argument** [reductio]" in md
    assert "    - ⇒ C" in md
    assert "## Sources" in md
    assert "mention" not in md.split("## Arguments")[1].split("##")[0]  # edge-linked, not a mention


def test_markdown_marks_mentions_and_truth_values():
    md = explain(_framework(), "Knowledge").to_markdown()
    assert "(asserted)" in md
    assert "; mention)" in md
    # 'Unrelated' has no edge to Knowledge but its definition says "knowledge".
    assert "## Mentioned in definitions of\n- Unrelated" in md
    assert str(explain(_framework(), "Knowledge")) == md


def test_markdown_for_bare_edge_endpoint():
    md = explain([Relation("A", "is-a", "B", id="r")], "B").to_markdown()
    assert md.startswith("# B\n")
    assert "- A —is-a→ B" in md


# --------------------------------------------------------------------------- #
# Container wrappers                                                          #
# --------------------------------------------------------------------------- #
def test_reading_explain():
    book = Reading(source="Text", predicates=Vocabulary("p", ["is-a"]), id_prefix="t_")
    with book.at("p.1"):
        book.universal("A", "First thing.")
        book.universal("B", "A kind of A.")
        book.relate("B", "is-a", "A")
        book.claim("A is fundamental.", truth_value=True, label="P")
    b = book.explain("A")
    assert b.definition == "First thing."
    assert [r.source for r in b.incoming] == ["B"]
    assert [p.label for p, _ in b.propositions] == ["P"]
    assert [c.name for c in b.mentioned_in] == ["B"]
    assert b.sources() == {"Text": ["p.1"]}


def test_repository_explain(tmp_path):
    repo = ValueRepository(data_dir=tmp_path)
    repo.add_values(_framework())
    b = repo.explain("JustifiedTrueBelief")
    assert b.kind == "concept"
    assert len(b.relations) == 4


def test_merge_result_explain_unites_sources():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    b = res.explain("Freedom")
    sources = set(b.sources())
    assert any("Kant" in s for s in sources)
    assert any("Kierkegaard" in s for s in sources)
    kant_only = explain(json.loads((ONTOLOGIES / "kant.json").read_text()), "Freedom")
    assert len(b.relations) > len(kant_only.relations)


def test_kant_freedom_brief():
    docs = json.loads((ONTOLOGIES / "kant.json").read_text(encoding="utf-8"))
    b = explain(docs, "Freedom")
    assert b.kind == "universal" and b.ontological_status == "abstract"
    assert b.by_predicate("out")["is-a"] == ["MoralConcept", "Postulate"]
    assert "MoralLaw" in b.by_predicate("in")["presupposes"]
    labels = {p.label for p, _ in b.propositions}
    assert "P-Postulates" in labels
    handles = {a.handle for a, _ in b.arguments}
    assert "Third-Antinomy-Resolution" in handles
    assert "Kant, Critique of Practical Reason (1788)" in b.sources()
