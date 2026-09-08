"""Tests for valuez.traversal -- neighborhoods, paths, topic subgraphs, how(A, B)."""
from pathlib import Path

import pytest

from valuez import (
    Concept,
    Graph,
    Individual,
    Instantiation,
    Reading,
    Relation,
    Universal,
    Vocabulary,
    traversal,
)
from valuez.repository import ValueRepository
from valuez.traversal import Hop, Neighborhood, Path as Walk

ONTOLOGIES = Path(__file__).resolve().parent.parent / "ontologies"


def _chain():
    """A small mixed-predicate graph used across the suite.

    Cell -part-of-> Tissue -part-of-> Organ -part-of-> Organism
    Human -is-a-> Animal -is-a-> LivingThing
    Socrates -instantiates-> Human
    Scarlet -grounds-> Red -grounds-> Colored
    Organism -is-a-> LivingThing          (cross-link)
    Isolated (named, no edges)
    """
    nodes = [
        Universal("Cell"),
        Universal("Tissue"),
        Universal("Organ"),
        Universal("Organism"),
        Universal("Human"),
        Universal("Animal"),
        Universal("LivingThing"),
        Universal("Scarlet"),
        Universal("Red"),
        Universal("Colored"),
        Individual("Socrates"),
        Concept("Isolated", definition="no edges"),
    ]
    rels = [
        Relation("Cell", "part-of", "Tissue", id="r1"),
        Relation("Tissue", "part-of", "Organ", id="r2"),
        Relation("Organ", "part-of", "Organism", id="r3"),
        Relation("Human", "is-a", "Animal", id="r4"),
        Relation("Animal", "is-a", "LivingThing", id="r5"),
        Instantiation("Socrates", "Human", id="r6"),
        Relation("Scarlet", "grounds", "Red", id="r7"),
        Relation("Red", "grounds", "Colored", id="r8"),
        Relation("Organism", "is-a", "LivingThing", id="r9"),
    ]
    return nodes, rels


def _graph():
    nodes, rels = _chain()
    return Graph.from_values(list(nodes) + list(rels))


# --------------------------------------------------------------------------- #
# Construction                                                                #
# --------------------------------------------------------------------------- #
def test_from_relations_picks_up_endpoints():
    g = Graph.from_relations([Relation("A", "is-a", "B")])
    assert set(g.nodes) == {"A", "B"}
    assert g.n_edges == 1


def test_from_values_keeps_isolated_nodes():
    g = _graph()
    assert "Isolated" in g
    assert g.neighbors("Isolated") == []
    assert g.neighborhood("Isolated", hops=2).nodes == ("Isolated",)


def test_from_values_accepts_document_dicts():
    rel = Relation("A", "is-a", "B", id="e1")
    node = Concept("C", id="n1")
    g = Graph.from_values([rel.to_dict(), node.to_dict()])
    assert set(g.nodes) == {"A", "B", "C"}


def test_rejects_non_relations():
    with pytest.raises(TypeError):
        Graph([Concept("A")])  # type: ignore[list-item]


# --------------------------------------------------------------------------- #
# Neighbors / incident / neighborhood                                         #
# --------------------------------------------------------------------------- #
def test_unknown_node_raises():
    g = _graph()
    with pytest.raises(ValueError, match="unknown node"):
        g.neighbors("NoSuch")
    with pytest.raises(ValueError, match="unknown node"):
        g.how("Human", "NoSuch")


def test_neighbors_respect_direction():
    g = _graph()
    assert g.neighbors("Tissue", direction="out") == ["Organ"]
    assert g.neighbors("Tissue", direction="in") == ["Cell"]
    assert g.neighbors("Tissue", direction="both") == ["Cell", "Organ"]


def test_neighbors_accept_concept_objects():
    g = _graph()
    assert g.neighbors(Universal("Human")) == ["Animal", "Socrates"]


def test_incident_filters_predicate():
    g = _graph()
    only_isa = g.incident("Organism", predicates="is-a")
    assert {r.predicate for r in only_isa} == {"is-a"}
    assert {r.source for r in only_isa} | {r.target for r in only_isa} == {"Organism", "LivingThing"}


def test_neighborhood_hops():
    g = _graph()
    n0 = g.neighborhood("Cell", hops=0)
    assert set(n0.nodes) == {"Cell"}
    assert n0.relations == ()

    n1 = g.neighborhood("Cell", hops=1)
    assert set(n1.nodes) == {"Cell", "Tissue"}

    n2 = g.neighborhood("Cell", hops=2)
    assert set(n2.nodes) == {"Cell", "Tissue", "Organ"}

    n3 = g.neighborhood("Cell", hops=3)
    assert "Organism" in n3
    # induced: the Organism -is-a-> LivingThing edge is included once Organism is in
    n4 = g.neighborhood("Cell", hops=4)
    assert "LivingThing" in n4


def test_neighborhood_out_does_not_walk_backward():
    g = _graph()
    nb = g.neighborhood("Tissue", hops=1, direction="out")
    assert set(nb.nodes) == {"Tissue", "Organ"}
    assert "Cell" not in nb


def test_neighborhood_predicate_filter():
    g = _graph()
    # Outgoing is-a from Human is the subsumption chain; Socrates is instantiates.
    nb = g.neighborhood("Human", hops=4, predicates="is-a", direction="out")
    assert set(nb.nodes) == {"Human", "Animal", "LivingThing"}
    assert "Socrates" not in nb
    both = g.neighborhood("Human", hops=1, predicates="is-a")
    assert "Socrates" not in both
    assert "Animal" in both


def test_neighborhood_rejects_negative_hops():
    with pytest.raises(ValueError):
        _graph().neighborhood("Human", hops=-1)


def test_bad_direction_raises():
    with pytest.raises(ValueError, match="direction"):
        _graph().neighbors("Human", direction="sideways")


# --------------------------------------------------------------------------- #
# Paths / how                                                                 #
# --------------------------------------------------------------------------- #
def test_shortest_path_is_directed_by_default():
    g = _graph()
    forward = g.shortest_path("Cell", "Organism")
    assert forward is not None
    assert forward.describe() == "Cell -part-of-> Tissue -part-of-> Organ -part-of-> Organism"
    assert g.shortest_path("Organism", "Cell") is None  # against the arrows


def test_how_is_undirected_and_shows_reverse_arrows():
    g = _graph()
    path = g.how("Organism", "Cell")
    assert path is not None
    assert path.describe() == "Organism <-part-of- Organ <-part-of- Tissue <-part-of- Cell"
    assert path.length == 3
    assert all(not hop.forward for hop in path.hops)


def test_how_disconnected_returns_none():
    g = _graph()
    assert g.how("Cell", "Scarlet") is None
    assert g.how("Isolated", "Human") is None


def test_how_identity_is_zero_hop():
    g = _graph()
    path = g.how("Human", "Human")
    assert path is not None
    assert path.length == 0
    assert path.describe() == "Human"


def test_how_with_predicate_filter():
    g = _graph()
    # Organism reaches LivingThing by is-a directly; Cell only reaches it via
    # part-of then is-a, so an is-a-only walk from Cell dies.
    assert g.how("Cell", "LivingThing", predicates="is-a") is None
    assert g.how("Human", "LivingThing", predicates="is-a").describe() == (
        "Human -is-a-> Animal -is-a-> LivingThing"
    )


def test_shortest_paths_from_batches_undirected_bfs():
    g = _graph()
    from_cell = g.shortest_paths_from("Cell")
    assert "Cell" not in from_cell
    assert from_cell["Organism"].describe() == (
        "Cell -part-of-> Tissue -part-of-> Organ -part-of-> Organism"
    )
    assert from_cell["LivingThing"].length == 4  # Cell..Organism -is-a-> LivingThing
    # Isolated is disconnected; a node with no edges reaches nobody.
    assert g.shortest_paths_from("Isolated") == {}
    # Directed: Organism cannot walk back to Cell.
    assert "Cell" not in g.shortest_paths_from("Organism", directed=True)
    assert g.shortest_paths_from("Organism", directed=False)["Cell"].length == 3
    # cutoff caps hop count (Tissue is 1 hop from Cell; Organ is 2).
    capped = g.shortest_paths_from("Cell", cutoff=1)
    assert set(capped) == {"Tissue"}
    with pytest.raises(ValueError, match="cutoff"):
        g.shortest_paths_from("Cell", cutoff=-1)


def test_paths_returns_shortest_first_and_respects_limit():
    # Two routes A -> C: A-B-C (2 hops) and A-C (1 hop).
    rels = [
        Relation("A", "p", "B", id="e1"),
        Relation("B", "p", "C", id="e2"),
        Relation("A", "q", "C", id="e3"),
    ]
    g = Graph.from_relations(rels)
    found = g.paths("A", "C", directed=True, cutoff=4)
    assert [p.describe() for p in found] == [
        "A -q-> C",
        "A -p-> B -p-> C",
    ]
    assert len(g.paths("A", "C", directed=True, limit=1)) == 1


def test_parallel_edges_surface_in_describe():
    rels = [
        Relation("A", "grounds", "B", id="e1"),
        Relation("A", "requires", "B", id="e2"),
    ]
    path = Graph.from_relations(rels).how("A", "B")
    assert path is not None
    assert path.describe() == "A -grounds|requires-> B"
    assert len(path.relations) == 2


def test_path_relations_carry_the_asserted_edge():
    rel = Relation("A", "is-a", "B", id="kept", reference=None)
    path = Graph.from_relations([rel]).how("A", "B")
    assert path.relations[0] is rel or path.relations[0] == rel
    assert path.relations[0].id == "kept"


# --------------------------------------------------------------------------- #
# Topic / subgraph                                                            #
# --------------------------------------------------------------------------- #
def test_topic_is_induced_neighborhood():
    g = _graph()
    topic = g.topic("Human", hops=1)
    assert set(topic.nodes) == {"Human", "Animal", "Socrates"}
    # induced: both the is-a and the instantiates edges
    preds = {r.predicate for r in topic.relations}
    assert preds == {"is-a", "instantiates"}
    assert "LivingThing" not in topic


def test_topic_multiple_seeds():
    g = _graph()
    topic = g.topic(["Cell", "Scarlet"], hops=1)
    assert "Tissue" in topic and "Red" in topic
    assert "Organ" not in topic and "Colored" not in topic


def test_subgraph_raises_on_unknown():
    with pytest.raises(ValueError, match="unknown node"):
        _graph().subgraph(["Human", "NoSuch"])


def test_neighborhood_as_graph_round_trips():
    nb = _graph().neighborhood("Red", hops=1)
    assert isinstance(nb, Neighborhood)
    g = nb.graph()
    assert set(g.nodes) == set(nb.nodes)
    assert len(g.relations) == len(nb.relations)


# --------------------------------------------------------------------------- #
# Functional helpers + container wrappers                                     #
# --------------------------------------------------------------------------- #
def test_module_level_helpers_match_graph_methods():
    _, rels = _chain()
    path = traversal.how(rels, "Human", "LivingThing")
    assert path is not None
    assert "is-a" in path.describe()
    nb = traversal.neighborhood(rels, "Cell", hops=2)
    assert "Organ" in nb


def test_reading_graph_wrapper():
    book = Reading(source="T", predicates=Vocabulary("p", ["is-a", "part-of"]))
    with book.at("p.1"):
        book.universal("A")
        book.universal("B")
        book.universal("C")
        book.relate("A", "is-a", "B")
        book.relate("B", "part-of", "C")
    g = book.graph()
    assert g.how("A", "C").describe() == "A -is-a-> B -part-of-> C"


def test_repository_graph_and_values(tmp_path):
    _, rels = _chain()
    repo = ValueRepository(data_dir=tmp_path)
    repo.add_values(rels)
    assert len(repo.values()) == len(rels)
    g = repo.graph()
    assert g.shortest_path("Cell", "Organism") is not None


def test_from_ontology_kant_space_intuition():
    g = Graph.from_ontology(ONTOLOGIES / "kant.json")
    assert "Space" in g and "Freedom" in g
    path = g.how("Space", "Intuition")
    assert path is not None
    assert "is-form-of" in path.describe()
    nb = g.neighborhood("Freedom", hops=1)
    assert nb.center == "Freedom"
    assert len(nb) > 1


def test_visualize_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = _graph().topic("Human", hops=2).visualize(tmp_path / "topic.html")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "html" in text.lower()


def test_hop_and_walk_equality():
    rel = Relation("A", "is-a", "B", id="e")
    h1 = Hop("A", "B", [rel])
    h2 = Hop("A", "B", [rel])
    assert h1 == h2
    p1 = Walk(["A", "B"], [h1])
    p2 = Walk(["A", "B"], [h2])
    assert p1 == p2
    assert len(p1) == 1
