"""Structural guard for examples/discovery_demo.py."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "discovery_demo",
    Path(__file__).resolve().parent.parent / "examples" / "discovery_demo.py",
)
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)


def test_demo_runs_and_writes_export(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    demo.main()
    out = capsys.readouterr().out
    assert "TranscendentalIdealism" in out
    assert "Anxiety" in out
    assert "Freedom" in out
    export = tmp_path / "crossings.json"
    assert export.exists()
    text = export.read_text()
    assert "TranscendentalIdealism" in text
    assert "join_points" in text
