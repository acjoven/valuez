"""Structural guard for examples/reading_session.py."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "reading_session",
    Path(__file__).resolve().parent.parent / "examples" / "reading_session.py",
)
rs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rs)


def test_reading_session_builds_and_validates():
    book = rs.build_reading()
    assert book.validate() == []
    s = book.stats()
    assert s["individuals"] == 2
    assert s["universals"] >= 10
    assert s["instantiations"] == 2
    assert s["arguments"] == 1


def test_reading_session_infers_stufenleiter_edge():
    book = rs.build_reading()
    inferred = {(e.source, e.target) for e in book.infer_transitive("is-a")}
    assert ("Category", "Representation") in inferred


def test_reading_session_provenance_attached():
    book = rs.build_reading()
    space = book.get("Space")
    assert space.reference is not None
    assert space.reference.locator == "A22/B36"
    assert "Critique of Pure Reason" in space.reference.source


def test_reading_session_roundtrips(tmp_path):
    from valuez.repository import ValueRepository

    book = rs.build_reading()
    path = book.export(tmp_path / "o.json", data_dir=tmp_path / "store")
    repo = ValueRepository.from_ontology(path, data_dir=tmp_path / "reload")
    ids = set(repo.query("[*].id"))
    assert ids == {v.id for v in book.values()}
