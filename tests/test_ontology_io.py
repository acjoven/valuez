"""Canonical single-file export/import of an ontology map."""
import json

from valuez import Concept, Reference, Relation, Scalar
from valuez.repository import ValueRepository


def _seed(repo):
    repo.add_values([
        Concept("Human", definition="rational animal", id="c_human"),
        Concept("Animal", id="c_animal"),
        Relation("Human", "is-a", "Animal", id="r_ha"),
        Scalar(42.0, unit="kg", id="s_mass", reference=Reference("scale#7")),
    ])


def test_export_is_sorted_json_array(tmp_path):
    repo = ValueRepository(data_dir=tmp_path / "store")
    _seed(repo)
    out = repo.export_ontology(tmp_path / "map.json")

    docs = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(docs, list)
    ids = [d["id"] for d in docs]
    assert ids == sorted(ids) == ["c_animal", "c_human", "r_ha", "s_mass"]


def test_export_is_deterministic(tmp_path):
    repo = ValueRepository(data_dir=tmp_path / "store")
    _seed(repo)
    first = repo.export_ontology(tmp_path / "a.json").read_text(encoding="utf-8")
    second = repo.export_ontology(tmp_path / "b.json").read_text(encoding="utf-8")
    assert first == second
    assert first.endswith("\n")


def test_export_creates_parent_dirs(tmp_path):
    repo = ValueRepository(data_dir=tmp_path / "store")
    _seed(repo)
    out = repo.export_ontology(tmp_path / "nested" / "dir" / "map.json")
    assert out.exists()


def test_load_ontology_roundtrips_into_fresh_store(tmp_path):
    src = ValueRepository(data_dir=tmp_path / "store")
    _seed(src)
    path = src.export_ontology(tmp_path / "map.json")

    dst = ValueRepository(data_dir=tmp_path / "store2")
    ids = dst.load_ontology(path)
    assert set(ids) == {"c_human", "c_animal", "r_ha", "s_mass"}

    human = dst.get_value("c_human")
    assert isinstance(human, Concept) and human.name == "Human"
    scalar = dst.get_value("s_mass")
    assert isinstance(scalar, Scalar) and scalar.is_grounded()


def test_from_ontology_classmethod(tmp_path):
    src = ValueRepository(data_dir=tmp_path / "store")
    _seed(src)
    path = src.export_ontology(tmp_path / "map.json")

    repo = ValueRepository.from_ontology(path, data_dir=tmp_path / "store2")
    assert sorted(repo.query("[].kind")) == ["concept", "concept", "relation", "scalar"]
    rel = repo.get_value("r_ha")
    assert isinstance(rel, Relation)
    assert (rel.source, rel.predicate, rel.target) == ("Human", "is-a", "Animal")
