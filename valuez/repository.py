# valuez/valuez/repository.py
from pathlib import Path
from dots.storage import JsonStorage
from dots.query import run_jmespath
from dots.graph import build_graph_from_docs, visualize_graph

class ValueRepository:
    """OOP cover over dots' functional storage/query/graph layer."""
    def __init__(self, data_dir: str | Path | None = None):
        self._store = JsonStorage.create(Path(data_dir) if data_dir else None)

    def add(self, source_json: str | Path, id_field: str = "id"):
        return self._store.ingest(Path(source_json), id_field=id_field)

    def query(self, expr: str):
        return run_jmespath(expr, self._store.load_all())

    def to_graph_html(self, out: str, source="source", target="target"):
        g = build_graph_from_docs(self._store.load_all(), source, target)
        return visualize_graph(g, Path(out))