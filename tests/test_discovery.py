"""Tests for valuez.discovery -- exclusive-to-exclusive paths created by a merge."""
from pathlib import Path

import pytest

from valuez import (
    Crossing,
    Universal,
    Relation,
    discover,
    merge_ontologies,
)
from valuez.merge import MergeReport, MergeResult

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _ab_universe():
    """Shared join plus exclusive legs: OnlyA -is-a-> Shared <-is-a- OnlyB."""
    a = [
        Universal("Shared", definition="from A", id="a_shared"),
        Universal("OnlyA", id="a_onlya"),
        Universal("IsolatedA", id="a_iso"),
        Relation("OnlyA", "is-a", "Shared", id="a_rel"),
    ]
    b = [
        Universal("Shared", definition="from B", id="b_shared"),
        Universal("OnlyB", id="b_onlyb"),
        Relation("OnlyB", "is-a", "Shared", id="b_rel"),
    ]
    return merge_ontologies([a, b], labels=["A", "B"])


# --------------------------------------------------------------------------- #
# Synthetic two-source universe                                               #
# --------------------------------------------------------------------------- #
def test_two_hop_crossing_via_the_join_point():
    res = _ab_universe()
    found = discover(res)
    assert found.sources == ("A", "B")
    assert found.join_points == ("Shared",)
    assert found.exclusive["A"] == ("IsolatedA", "OnlyA")
    assert found.exclusive["B"] == ("OnlyB",)
    # IsolatedA has no edges, so it never starts a crossing.
    pairs = {(c.start, c.end, c.from_source, c.to_source) for c in found.crossings}
    assert ("OnlyA", "OnlyB", "A", "B") in pairs
    assert ("OnlyB", "OnlyA", "B", "A") in pairs
    assert found.total == 2
    for crossing in found.crossings:
        assert crossing.hops == 2
        assert crossing.via == ("Shared",)
        assert "Shared" in crossing.path.describe()


def test_merge_result_discover_matches_module_function():
    res = _ab_universe()
    assert [c.to_dict() for c in res.discover().crossings] == [
        c.to_dict() for c in discover(res).crossings
    ]


def test_between_and_via_filter_the_ranked_list():
    found = discover(_ab_universe())
    ab = found.between("A", "B")
    ba = found.between("B", "A")
    assert len(ab) == 1 and ab[0].start == "OnlyA" and ab[0].end == "OnlyB"
    assert len(ba) == 1 and ba[0].start == "OnlyB"
    assert found.via("Shared") == found.crossings
    assert found.via("NoSuch") == ()


def test_direct_exclusive_edge_is_not_a_crossing():
    # A dangling A->OnlyB edge is satisfied after merge, but never visits a join.
    a = [
        Universal("Shared", id="a_s"),
        Universal("OnlyA", id="a_a"),
        Relation("OnlyA", "is-a", "Shared", id="a_join"),
        Relation("OnlyA", "related-to", "OnlyB", id="a_direct"),
    ]
    b = [
        Universal("Shared", id="b_s"),
        Universal("OnlyB", id="b_b"),
        Relation("OnlyB", "is-a", "Shared", id="b_join"),
    ]
    found = discover(merge_ontologies([a, b], labels=["A", "B"]))
    # Shortest OnlyA~OnlyB is the 1-hop direct edge (no join) -> skipped.
    # Reverse OnlyB~OnlyA is 2 hops via Shared -> kept.
    pairs = {(c.start, c.end) for c in found.crossings}
    assert ("OnlyA", "OnlyB") not in pairs
    assert ("OnlyB", "OnlyA") in pairs


def test_disjoint_universes_have_no_crossings():
    a = [Universal("A1", id="a1")]
    b = [Universal("B1", id="b1")]
    found = discover(merge_ontologies([a, b], labels=["A", "B"]))
    assert found.crossings == ()
    assert found.total == 0
    assert found.join_points == ()


def test_limit_truncates_ranked_list_but_hubs_use_the_full_set():
    a = [
        Universal("Shared", id="a_s"),
        Universal("A1", id="a1"),
        Universal("A2", id="a2"),
        Relation("A1", "is-a", "Shared", id="a_r1"),
        Relation("A2", "is-a", "Shared", id="a_r2"),
    ]
    b = [
        Universal("Shared", id="b_s"),
        Universal("B1", id="b1"),
        Universal("B2", id="b2"),
        Relation("B1", "is-a", "Shared", id="b_r1"),
        Relation("B2", "is-a", "Shared", id="b_r2"),
    ]
    res = merge_ontologies([a, b], labels=["A", "B"])
    all_found = discover(res, limit=0)
    # 2x2 pairs, both directions = 8 crossings, all via Shared.
    assert all_found.total == 8
    assert all_found.hubs == (("Shared", 8),)
    truncated = discover(res, limit=1)
    assert truncated.total == 8
    assert len(truncated.crossings) == 1
    assert truncated.hubs == (("Shared", 8),)
    # Ranked shortest-first, then lexicographic start/end/sources.
    first = truncated.crossings[0]
    assert (first.start, first.end) == ("A1", "B1")


def test_cutoff_drops_longer_crossings():
    # A2 - A1 - Shared - B1  is 3 hops; default cutoff=3 keeps it, cutoff=2 drops it.
    a = [
        Universal("Shared", id="a_s"),
        Universal("A1", id="a1"),
        Universal("A2", id="a2"),
        Relation("A2", "is-a", "A1", id="a_chain"),
        Relation("A1", "is-a", "Shared", id="a_join"),
    ]
    b = [
        Universal("Shared", id="b_s"),
        Universal("B1", id="b1"),
        Relation("B1", "is-a", "Shared", id="b_join"),
    ]
    res = merge_ontologies([a, b], labels=["A", "B"])
    tight = discover(res, cutoff=2, limit=0)
    starts_ends = {(c.start, c.end) for c in tight.crossings}
    assert ("A1", "B1") in starts_ends
    assert ("A2", "B1") not in starts_ends
    wide = discover(res, cutoff=3, limit=0)
    assert ("A2", "B1") in {(c.start, c.end) for c in wide.crossings}


def test_directed_walk_follows_arrows_only():
    # OnlyA -> Shared <- OnlyB. Undirected both ways; directed only A->B fails
    # because Shared has no outgoing edge to OnlyB.
    res = _ab_universe()
    undirected = discover(res, directed=False)
    directed = discover(res, directed=True)
    assert undirected.total == 2
    assert directed.total == 0


def test_discover_accepts_raw_sources():
    a = [Universal("Shared", id="a_s"), Universal("OnlyA", id="a_a"),
         Relation("OnlyA", "is-a", "Shared", id="a_r")]
    b = [Universal("Shared", id="b_s"), Universal("OnlyB", id="b_b"),
         Relation("OnlyB", "is-a", "Shared", id="b_r")]
    found = discover([a, b])
    assert found.total == 2


def test_rejects_bad_cutoff_and_limit():
    res = _ab_universe()
    with pytest.raises(ValueError, match="cutoff"):
        discover(res, cutoff=0)
    with pytest.raises(ValueError, match="limit"):
        discover(res, limit=-1)


def test_empty_node_sources_raises():
    with pytest.raises(ValueError, match="node_sources"):
        discover(MergeResult([], MergeReport()))


def test_summary_and_to_dict_round_trip_shape():
    found = discover(_ab_universe())
    text = found.summary()
    assert "2 crossing(s)" in text
    assert "Shared" in text
    assert "OnlyA" in text
    d = found.to_dict()
    assert d["total"] == 2
    assert d["join_points"] == ["Shared"]
    assert d["hubs"] == [{"join": "Shared", "crossings": 2}]
    assert {c["start"] for c in d["crossings"]} == {"OnlyA", "OnlyB"}
    crossing = found.crossings[0]
    assert isinstance(crossing, Crossing)
    assert "OnlyA" in repr(crossing) or "OnlyB" in repr(crossing)
    assert "Discovery" in repr(found)


def test_n_way_pairs_each_exclusive_pair():
    a = [Universal("Join", id="a_j"), Universal("AOnly", id="a_o"),
         Relation("AOnly", "is-a", "Join", id="a_r")]
    b = [Universal("Join", id="b_j"), Universal("BOnly", id="b_o"),
         Relation("BOnly", "is-a", "Join", id="b_r")]
    c = [Universal("Join", id="c_j"), Universal("COnly", id="c_o"),
         Relation("COnly", "is-a", "Join", id="c_r")]
    found = discover(merge_ontologies([a, b, c], labels=["A", "B", "C"]), limit=0)
    # 3 pairs * 2 directions
    assert found.total == 6
    assert set(found.sources) == {"A", "B", "C"}
    assert found.join_points == ("Join",)
    dirs = {(c.from_source, c.to_source) for c in found.crossings}
    assert dirs == {("A", "B"), ("B", "A"), ("A", "C"), ("C", "A"), ("B", "C"), ("C", "B")}


# --------------------------------------------------------------------------- #
# Integration on the committed Kant + Kierkegaard ontologies                  #
# --------------------------------------------------------------------------- #
def test_kant_kierkegaard_crossing_through_freedom():
    res = merge_ontologies([ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"])
    found = discover(res, cutoff=2, limit=0)
    assert "kant" in found.sources and "kierkegaard" in found.sources
    assert "Freedom" in found.join_points
    assert "TranscendentalIdealism" in found.exclusive["kant"]
    assert "Anxiety" in found.exclusive["kierkegaard"]
    pairs = {(c.start, c.end) for c in found.crossings}
    assert ("TranscendentalIdealism", "Anxiety") in pairs
    assert ("Anxiety", "TranscendentalIdealism") in pairs
    ti = next(
        c for c in found.crossings
        if c.start == "TranscendentalIdealism" and c.end == "Anxiety"
    )
    assert ti.from_source == "kant" and ti.to_source == "kierkegaard"
    assert "Freedom" in ti.via
    assert ti.hops == 2
    hub_names = [name for name, _ in found.hubs]
    assert hub_names[0] == "Freedom"
    # MergeResult.discover is the same walk.
    via_freedom = res.discover(cutoff=2, limit=0).via("Freedom")
    assert any(c.start == "TranscendentalIdealism" and c.end == "Anxiety" for c in via_freedom)


def test_kant_kierkegaard_wrapper_and_summary():
    found = discover(
        [ONTOLOGIES / "kant.json", ONTOLOGIES / "kierkegaard.json"],
        cutoff=2,
        limit=12,
    )
    assert found.total > len(found.crossings) == 12
    text = found.summary()
    assert "kant" in text and "kierkegaard" in text
    assert "Freedom" in text
