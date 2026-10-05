"""Structural guard for examples/concept_brief.py."""
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "concept_brief",
    Path(__file__).resolve().parent.parent / "examples" / "concept_brief.py",
)
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)


def test_demo_writes_briefs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    demo.main()
    out = capsys.readouterr().out
    assert "# Freedom" in out
    assert "Same node in the merged universe" in out
    kant = (tmp_path / "freedom_kant.md").read_text(encoding="utf-8")
    universe = (tmp_path / "freedom_universe.md").read_text(encoding="utf-8")
    assert "## Relations" in kant
    assert "Kierkegaard" not in kant
    assert "Kierkegaard" in universe
    data = json.loads((tmp_path / "freedom_universe.json").read_text(encoding="utf-8"))
    assert data["name"] == "Freedom"
