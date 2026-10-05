# valuez/valuez/repository.py
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable
from dotz.storage import JsonStorage
from dotz.query import run_jmespath
from dotz.graph import build_graph_from_docs, visualize_graph

from .values import Value

class ValueRepository:
    """OOP cover over dotz' functional storage/query/graph layer."""
    def __init__(self, data_dir: str | Path | None = None):
        self._store = JsonStorage.create(Path(data_dir) if data_dir else None)

    def add(self, source_json: str | Path, id_field: str = "id"):
        return self._store.ingest(Path(source_json), id_field=id_field)

    def add_value(self, value: Value):
        """Persist a single Value object, keyed by its ``id``."""
        return self.add_values([value])

    def add_values(self, values: Iterable[Value]):
        """Persist Value objects by serializing them through dotz storage."""
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

    def export_ontology(self, path: str | Path) -> Path:
        """Write the whole store to one canonical JSON array (the artifact to commit).

        The ``dotz`` store keeps one file per document (often UUID-named), which
        makes for noisy, hard-to-review git history. This method serializes every
        stored document into a single file, sorted by ``id`` and with sorted keys,
        so repeated exports produce minimal, deterministic diffs. Commit this file
        (see the ``ontologies/`` convention) and treat the expanded per-document
        store as a regenerable local cache.
        """
        path = Path(path)
        docs = sorted(self._store.load_all(), key=lambda d: str(d.get("id", "")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(docs, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path

    def load_ontology(self, path: str | Path) -> list[str]:
        """Ingest a canonical JSON array produced by :meth:`export_ontology`.

        Documents are keyed by ``id``, so re-loading updates in place. For a clean
        rebuild (so removed documents disappear), load into a fresh ``data_dir``.
        Returns the ingested document ids.
        """
        return self._store.ingest(Path(path), id_field="id")

    @classmethod
    def from_ontology(cls, path: str | Path, data_dir: str | Path | None = None) -> "ValueRepository":
        """Build a repository from a canonical ontology file.

        Convenience for the read side: rehydrate a committed ``ontologies/*.json``
        into a (typically temporary/local) store you can query and visualize.
        """
        repo = cls(data_dir=data_dir)
        repo.load_ontology(path)
        return repo

    def query(self, expr: str):
        return run_jmespath(expr, self._store.load_all())

    def values(self):
        """Rehydrate every stored document as a :class:`~valuez.values.Value`."""
        return [Value.from_dict(doc) for doc in self._store.load_all()]

    def graph(self):
        """Relation graph over stored documents, for neighborhood / path queries."""
        from .traversal import Graph

        return Graph.from_documents(self._store.load_all())

    def analyze(self, **kwargs):
        """Inference + tension detection over stored documents. See :func:`valuez.analyze`."""
        from .analysis import analyze

        return analyze(self._store.load_all(), **kwargs)

    def explain(self, name, **kwargs):
        """A readable :class:`~valuez.briefs.Brief` for one stored concept."""
        from .briefs import explain

        return explain(self._store.load_all(), name, **kwargs)

    def bibliography(self, **kwargs):
        """Collect the sources cited by all stored documents into a ReferenceRepository.

        Rehydrates each document's ``reference`` and gathers the bibliographic
        (keyed) sources; see ``ReferenceRepository.from_values`` for options.
        """
        from .bibliography import ReferenceRepository
        from .values import Reference

        refs = [
            Reference.from_dict(doc["reference"])
            for doc in self._store.load_all()
            if doc.get("reference")
        ]
        return ReferenceRepository.from_values(refs, **kwargs)

    def to_graph_html(self, out: str, source="source", target="target"):
        g = build_graph_from_docs(self._store.load_all(), source, target)
        return visualize_graph(g, Path(out))