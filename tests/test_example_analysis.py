"""Structural guard for examples/analysis_demo.py."""
import importlib.util
import json
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "analysis_demo",
    Path(__file__).resolve().parent.parent / "examples" / "analysis_demo.py",
)
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)


def test_demo_runs_and_writes_kant_analysis(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    demo.main()
    out = capsys.readouterr().out
    assert "transitivity" in out
    assert "Gettier-Argument" in out
    assert "defeated" in out
    assert "clash" in out
    assert "cycle" in out
    data = json.loads((tmp_path / "analysis_kant.json").read_text(encoding="utf-8"))
    assert "derived" in data and "tensions" in data and "gaps" in data
