"""Structural guard for examples/traversal_demo.py."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "traversal_demo",
    Path(__file__).resolve().parent.parent / "examples" / "traversal_demo.py",
)
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)


def test_demo_runs_and_writes_topic_graph(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    demo.main()
    out = capsys.readouterr().out
    assert "Space -is-form-of-> Intuition" in out
    assert "Freedom" in out
    assert (tmp_path / "freedom_topic.html").exists()
