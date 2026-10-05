"""Tests for valuez.merge -- joining ontologies into one universe by node name."""
import importlib.util
from pathlib import Path

import pytest

from valuez import (
    Individual,
    Instantiation,
    Relation,
    Scalar,
    Universal,
    merge_ontologies,
)
from valuez.repository import ValueRepository

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _load_example(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent.parent / "examples" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Core semantics on small, synthetic ontologies                               #
# --------------------------------------------------------------------------- #
def test_common_node_is_joined_and_bridges_both_graphs():
    # Two ontologies that share the universal "Shared".
    a = [
        Universal("Shared", definition="from A", id="a_shared"),
        Universal("OnlyA", id="a_onlya"),
        Relation("OnlyA", "is-a", "Shared", id="a_rel"),
    ]
    b = [
        Universal("Shared", definition="from B", id="b_shared"),
        Universal("OnlyB", id="b_onlyb"),
        Relation("OnlyB", "is-a", "Shared", id="b_rel"),
    ]
    res = merge_ontologies([a, b], labels=["A", "B"])
    shared = [d for d in res.documents if d.get("name") == "Shared"]
    assert len(shared) == 1, "the common node must collapse to one"
    # both edges now attach to the single shared node -> the graphs are connected
    incident = [d for d in res.documents
                if d.get("kind") == "relation" and d.get("target") == "Shared"]
    assert {d["id"] for d in incident} == {"a_rel", "b_rel"}
    assert res.report.join_points == {"Shared": ["A", "B"]}
    assert res.report.node_sources["Shared"] == ["A", "B"]
    assert res.report.node_sources["OnlyA"] == ["A"]
    assert res.report.node_sources["OnlyB"] == ["B"]


def test_no_dangling_endpoints_after_merge():
    a = [Universal("X", id="a_x"), Relation("X", "is-a", "Y", id="a_r")]
    b = [Universal("Y", id="b_y")]
    res = merge_ontologies([a, b])
    # X (from A) and Y (from B) both exist in the union -> the edge is satisfied
    assert res.report.dangling_edges == []


def test_disjoint_ontologies_have_no_join_points():
    a = [Universal("A1", id="a1"), Universal("A2", id="a2")]
    b = [Universal("B1", id="b1")]
    res = merge_ontologies([a, b])
    assert res.report.join_points == {}
    assert res.report.output_total == 3


# --------------------------------------------------------------------------- #
# Conflict handling                                                            #
# --------------------------------------------------------------------------- #
def test_field_conflict_first_and_last_policies():
    a = [Universal("N", definition="A-def", ontological_status="abstract", id="a_n")]
    b = [Universal("N", definition="B-def", ontological_status="existential", id="b_n")]

    first = merge_ontologies([a, b], labels=["A", "B"], on_conflict="first")
    node_first = [d for d in first.documents if d["name"] == "N"][0]
    assert node_first["definition"] == "A-def"
    assert "N" in first.report.field_conflicts
    assert set(first.report.field_conflicts["N"]) == {"definition", "ontological_status"}

    last = merge_ontologies([a, b], labels=["A", "B"], on_conflict="last")
    node_last = [d for d in last.documents if d["name"] == "N"][0]
    assert node_last["definition"] == "B-def"


def test_missing_field_is_filled_from_the_other_source():
    a = [Universal("N", id="a_n")]  # no definition
    b = [Universal("N", definition="B-def", id="b_n")]
    res = merge_ontologies([a, b], on_conflict="first")
    node = [d for d in res.documents if d["name"] == "N"][0]
    assert node["definition"] == "B-def"  # filled in, not a conflict
    assert "N" not in res.report.field_conflicts


def test_on_conflict_raise_refuses_semantic_collision():
    a = [Universal("N", definition="A-def", id="a_n")]
    b = [Universal("N", definition="B-def", id="b_n")]
    with pytest.raises(ValueError):
        merge_ontologies([a, b], on_conflict="raise")


def test_type_conflict_is_recorded():
    a = [Universal("Freedom", id="a_f")]
    b = [Individual("Freedom", id="b_f")]
    res = merge_ontologies([a, b], labels=["A", "B"])
    assert "Freedom" in res.report.type_conflicts
    assert res.report.type_conflicts["Freedom"] == {"A": "universal", "B": "individual"}
    with pytest.raises(ValueError):
        merge_ontologies([a, b], on_conflict="raise")


# --------------------------------------------------------------------------- #
# Edges + ids                                                                 #
# --------------------------------------------------------------------------- #
def test_identical_edges_are_deduplicated_with_shared_provenance():
    a = [Universal("A", id="a_a"), Universal("B", id="a_b"),
         Relation("A", "is-a", "B", id="a_rel")]
    b = [Relation("A", "is-a", "B", id="b_rel")]
    res = merge_ontologies([a, b], labels=["A", "B"])
    triples = [(d["source"], d["predicate"], d["target"]) for d in res.documents
               if d.get("kind") == "relation"]
    assert triples == [("A", "is-a", "B")]  # collapsed to one
    assert res.report.edges_deduped == 1
    assert len(res.report.shared_edges) == 1

    kept = merge_ontologies([a, b], dedupe_edges=False)
    kept_edges = [d for d in kept.documents if d.get("kind") == "relation"]
    assert len(kept_edges) == 2


def test_instantiation_edges_join_through_shared_universal():
    a = [Individual("KantMan", id="a_i"), Universal("Philosopher", id="a_u"),
         Instantiation("KantMan", "Philosopher", id="a_inst")]
    b = [Individual("KierMan", id="b_i"), Universal("Philosopher", id="b_u"),
         Instantiation("KierMan", "Philosopher", id="b_inst")]
    res = merge_ontologies([a, b])
    philosophers = [d for d in res.documents if d.get("name") == "Philosopher"]
    assert len(philosophers) == 1
    insts = [d for d in res.documents if d.get("kind") == "instantiation"]
    assert {d["target"] for d in insts} == {"Philosopher"}
    assert {d["source"] for d in insts} == {"KantMan", "KierMan"}


def test_id_collision_is_renamed():
    a = [Scalar(1.0, id="dup")]
    b = [Scalar(2.0, id="dup")]
    res = merge_ontologies([a, b])
    ids = sorted(d["id"] for d in res.documents)
    assert ids == ["dup", "dup__2"]
    assert res.report.id_collisions == [("dup", "dup__2")]


def test_exact_duplicate_document_is_dropped():
    a = [Scalar(1.0, id="same")]
    b = [Scalar(1.0, id="same")]
    res = merge_ontologies([a, b])
    assert res.report.output_total == 1
    assert res.report.id_collisions == []


# --------------------------------------------------------------------------- #
# Integration on the committed Kant + Kierkegaard ontologies                   #
# --------------------------------------------------------------------------- #
def test_real_merge_join_points_match_declared_anchors():
    kier = _load_example("kierkegaard_ontology")
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    assert set(res.report.join_points) == set(kier.MERGE_ANCHORS)
    # each join point drew from both sources
    for name, labels in res.report.join_points.items():
        assert set(labels) == {"kant", "kierkegaard"}


def test_real_merge_flags_semantic_collisions_and_stays_integral():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    # clean matches carry no field conflict; collisions do
    assert "Philosopher" not in res.report.field_conflicts
    for name in ("Existence", "Freedom", "God", "Reason"):
        assert name in res.report.field_conflicts
    # nine names collapse 2->1, so output is nine docs fewer than the inputs
    assert res.report.output_total == res.report.input_total - len(res.report.join_points)
    assert res.report.dangling_edges == []
    assert res.report.type_conflicts == {}


def test_real_merge_exports_and_roundtrips(tmp_path):
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    path = res.export(tmp_path / "universe.json")
    reloaded = ValueRepository.from_ontology(path, data_dir=tmp_path / "store")
    assert len(reloaded.query("[]")) == res.report.output_total
    freedom = reloaded.get_value("k_freedom")
    assert isinstance(freedom, Universal)  # single joined node, Kant's id kept (first)


def test_result_helpers_partition_documents():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    n_nodes = len(res.named_nodes())
    n_edges = len(res.relations())
    assert n_nodes > 100 and n_edges > 300
    assert n_nodes + n_edges <= res.report.output_total
    assert res.report.named_nodes_out == n_nodes


def test_report_summary_and_dict():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    text = res.report.summary()
    assert "Join points" in text and "Freedom" in text
    d = res.report.to_dict()
    assert d["edges"]["out"] == res.report.edges_out
    assert set(d["join_points"]) == set(res.report.join_points)
    assert set(d["node_sources"]) == {n.name for n in res.named_nodes()}
    assert d["node_sources"]["Freedom"] == ["kant", "kierkegaard"]
    assert d["node_sources"]["Anxiety"] == ["kierkegaard"]
    assert d["node_sources"]["TranscendentalIdealism"] == ["kant"]


# --------------------------------------------------------------------------- #
# Alias / sameAs joining (curated cross-name equivalence)                      #
# --------------------------------------------------------------------------- #
def test_alias_joins_differently_named_nodes():
    a = [Universal("Soul", definition="thinking subject", id="a_soul"),
         Universal("Anxiety", id="a_anx"),
         Relation("Anxiety", "reveals", "Soul", id="a_rel")]
    b = [Universal("TheSelf", definition="relates to itself", id="b_self"),
         Universal("Despair", id="b_dsp"),
         Relation("Despair", "afflicts", "TheSelf", id="b_rel")]
    res = merge_ontologies([a, b], labels=["A", "B"], aliases=[["TheSelf", "Soul"]])
    # one canonical node named "TheSelf"; "Soul" is gone
    selves = [d for d in res.documents if d.get("name") in ("Soul", "TheSelf")]
    assert [d["name"] for d in selves] == ["TheSelf"]
    # edges from both sources now point at the canonical node
    targets = {d["target"] for d in res.documents if d.get("kind") == "relation"}
    assert targets == {"TheSelf"}
    assert res.report.aliases_applied == {"TheSelf": ["Soul", "TheSelf"]}
    assert "TheSelf" in res.report.join_points
    assert res.report.dangling_edges == []


def test_alias_dict_form_and_lone_rename():
    # a single source, alias-renamed even without another source to join
    a = [Universal("Soul", id="a_soul"),
         Universal("Anxiety", id="a_anx"),
         Relation("Anxiety", "reveals", "Soul", id="a_rel")]
    res = merge_ontologies([a], aliases={"Soul": "TheSelf"})
    node = [d for d in res.documents if d.get("kind") == "universal"]
    assert {d["name"] for d in node} == {"TheSelf", "Anxiety"}
    edge = [d for d in res.documents if d.get("kind") == "relation"][0]
    assert edge["target"] == "TheSelf"
    assert res.report.aliases_applied == {"TheSelf": ["Soul"]}
    assert res.report.dangling_edges == []


def test_alias_dedupes_edges_across_names():
    a = [Universal("P", id="a_p"), Universal("Soul", id="a_soul"),
         Relation("P", "is-a", "Soul", id="a_rel")]
    b = [Universal("TheSelf", id="b_self"),
         Relation("P", "is-a", "TheSelf", id="b_rel")]
    res = merge_ontologies([a, b], aliases=[["TheSelf", "Soul"]])
    rels = [d for d in res.documents if d.get("kind") == "relation"]
    assert len(rels) == 1  # "P is-a Soul" and "P is-a TheSelf" collapse
    assert rels[0]["target"] == "TheSelf"
    assert res.report.edges_deduped == 1
    assert len(res.report.shared_edges) == 1


def test_alias_conflicting_map_raises():
    with pytest.raises(ValueError):
        merge_ontologies([[Universal("B", id="b")]], aliases=[["A", "B"], ["C", "B"]])


def test_node_sources_are_keyed_by_canonical_name():
    a = [Universal("Soul", id="a_soul"), Universal("OnlyA", id="a_o")]
    b = [Universal("TheSelf", id="b_self")]
    res = merge_ontologies([a, b], labels=["A", "B"], aliases=[["TheSelf", "Soul"]])
    assert res.report.node_sources["TheSelf"] == ["A", "B"]
    assert "Soul" not in res.report.node_sources
    assert res.report.node_sources["OnlyA"] == ["A"]


def test_bridges_helper_matches_report_count():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    assert len(res.bridges()) == res.report.bridge_edges
    assert res.report.bridge_edges > 0
    joins = set(res.report.join_points)
    for edge in res.bridges():
        assert edge.source in joins or edge.target in joins


def test_real_merge_alias_soul_theself_adds_one_join():
    base = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    aligned = merge_ontologies(
        [ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
        aliases=[["TheSelf", "Soul"]],
    )
    assert aligned.report.join_point_count == base.report.join_point_count + 1
    assert aligned.report.aliases_applied == {"TheSelf": ["Soul", "TheSelf"]}
    selves = [d for d in aligned.documents if d.get("name") in ("Soul", "TheSelf")]
    assert [d["name"] for d in selves] == ["TheSelf"]  # one canonical node
    assert aligned.report.node_sources["TheSelf"] == ["kant", "kierkegaard"]
    assert aligned.report.dangling_edges == []


def test_report_dict_has_new_fields():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
                           aliases=[["TheSelf", "Soul"]])
    d = res.report.to_dict()
    assert d["bridge_edges"] == res.report.bridge_edges
    assert d["aliases_applied"] == {"TheSelf": ["Soul", "TheSelf"]}
    assert d["node_sources"]["TheSelf"] == ["kant", "kierkegaard"]
    assert "node_provenance" not in d
    assert "type_conflicts" in d


def test_example_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    merge = _load_example("merge_universe")
    merge.main()
    assert (tmp_path / "universe.json").exists()
