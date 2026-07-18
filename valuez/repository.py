# valuez/valuez/repository.py
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable
from dots.storage import JsonStorage
from dots.query import run_jmespath
from dots.graph import build_graph_from_docs, visualize_graph

from .values import Value

class ValueRepository:
    """OOP cover over dots' functional storage/query/graph layer."""
    def __init__(self, data_dir: str | Path | None = None):
        self._store = JsonStorage.create(Path(data_dir) if data_dir else None)

    def add(self, source_json: str | Path, id_field: str = "id"):
        return self._store.ingest(Path(source_json), id_field=id_field)

    def add_value(self, value: Value):
        """Persist a single Value object, keyed by its ``id``."""
        return self.add_values([value])

    def add_values(self, values: Iterable[Value]):
        """Persist Value objects by serializing them through dots storage."""
        docs = [v.to_dict() for v in values]
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(docs, tmp, ensure_ascii=False)
            tmp.close()
            return self._store.ingest(Path(tmp.name), id_field="id")
        finally:
            os.unlink(tmp.name)

    def get_value(self, doc_id: str) -> Value | None:
        """Load a stored document and rehydrate it as a Value (or None)."""
        doc = self._store.load(doc_id)
        return Value.from_dict(doc) if doc is not None else None

    def query(self, expr: str):
        return run_jmespath(expr, self._store.load_all())

    def to_graph_html(self, out: str, source="source", target="target"):
        g = build_graph_from_docs(self._store.load_all(), source, target)
        return visualize_graph(g, Path(out))