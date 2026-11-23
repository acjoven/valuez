"""Structural guard for examples/quickstart.py (the README quickstart)."""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "quickstart",
    Path(__file__).resolve().parent.parent / "examples" / "quickstart.py",
)
qs = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(qs)


def test_quickstart_number_is_sourced():
    h = qs.sourced_number()
    assert (h.low, h.high, h.unit) == (2, 25, "W/(m^2*K)")
    assert h.is_grounded()
    assert h.reference.locator == "Table 1.1"


def test_quickstart_reading_builds_and_validates():
    book = qs.build_reading()
    assert book.validate() == []
    stats = book.stats()
    assert stats["concepts"] == 6
    assert stats["relations"] == 5


def test_quickstart_citation_rides_along():
    book = qs.build_reading()
    assert book.get("HeatTransfer").reference.locator == "Section 1.1"
    free = book.get("FreeConvection")
    assert free.reference.locator == "Section 1.2.2"
    assert free.reference.source == qs.TEXTBOOK
    assert all(v.is_grounded() for v in book.values())


def test_quickstart_infers_and_traverses():
    book = qs.build_reading()
    inferred = {(e.source, e.target) for e in book.infer_transitive("is-a")}
    assert inferred == {
        ("FreeConvection", "HeatTransfer"),
        ("ForcedConvection", "HeatTransfer"),
    }
    path = str(book.graph().how("FreeConvection", "Radiation"))
    assert path == "FreeConvection -is-a-> Convection -is-a-> HeatTransfer <-is-a- Radiation"


def test_quickstart_rejects_undeclared_endpoint_and_predicate():
    book = qs.build_reading()
    with pytest.raises(ValueError, match="not a declared concept"):
        book.relate("FreeConvection", "is-a", "Advection")
    with pytest.raises(ValueError, match="not in vocabulary"):
        book.relate("FreeConvection", "part-of", "Convection")


def test_quickstart_main_runs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    qs.main()
    out = capsys.readouterr().out
    assert "h, free convection in gases: 2 to 25 W/(m^2*K)" in out
    assert "inferred: FreeConvection is-a HeatTransfer" in out
    assert (tmp_path / "quickstart.json").exists()
