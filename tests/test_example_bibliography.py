"""Structural guard for examples/bibliography_demo.py."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pybtex")

_SPEC = importlib.util.spec_from_file_location(
    "bibliography_demo",
    Path(__file__).resolve().parent.parent / "examples" / "bibliography_demo.py",
)
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)


def test_demo_runs_and_writes_bibtex(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    demo.main()
    out = capsys.readouterr().out
    assert "Imported 3 sources" in out
    bib = (tmp_path / "sources.bib").read_text()
    assert "@book{incropera2007" in bib
    assert "@article{churchill1975" in bib
