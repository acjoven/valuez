"""BibTeX-backed source management for valuez references.

Where :class:`~valuez.values.Reference` is a *pure* provenance record (it never
imports a bibliography backend), this module adds the machinery to treat those
references as first-class bibliographic sources:

- :func:`reference_to_entry` / :func:`entry_to_reference` convert between a
  :class:`~valuez.Reference` and a ``pybtex`` ``Entry``.
- :class:`ReferenceRepository` is a keyed, de-duplicated collection of sources
  that can import/export ``.bib`` files and render a formatted bibliography.

The ``pybtex`` dependency is **optional**, mirroring how :mod:`valuez.units`
treats ``pint``: importing this module never fails, the pure-Python parts of the
repository (add / get / iterate) work without ``pybtex``, and only the
BibTeX-specific operations (:meth:`~ReferenceRepository.import_bibtex`,
:meth:`~ReferenceRepository.export_bibtex`,
:meth:`~ReferenceRepository.format_bibliography`) require it — raising a clear,
actionable error if it is missing.

Normalizing sources this way is a natural extension of the ground-truthing goal:
instead of every value embedding its own copy of a citation string, many values
can share one keyed :class:`~valuez.Reference` (``repo.reference("kant1998")``),
and the whole set of sources an ontology cites can be exported as a bibliography.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from .values import Reference

__all__ = [
    "pybtex_available",
    "reference_to_entry",
    "entry_to_reference",
    "ReferenceRepository",
]


def _try_import_pybtex() -> Any:
    try:
        import pybtex.database as _db  # noqa: F401

        return _db
    except Exception:  # pragma: no cover - exercised only without pybtex
        return None


_PYBTEX_DB = _try_import_pybtex()
pybtex_available: bool = _PYBTEX_DB is not None


def _require_pybtex() -> Any:
    if _PYBTEX_DB is None:  # pragma: no cover - exercised only without pybtex
        raise ImportError(
            "this operation requires the optional 'pybtex' dependency; "
            "install it with `pip install pybtex` (or `pip install -r requirements.txt`)"
        )
    return _PYBTEX_DB


def reference_to_entry(reference: Reference) -> Tuple[str, Any]:
    """Convert a :class:`~valuez.Reference` to a ``(key, pybtex.Entry)`` pair.

    Requires an ``entry_type`` (BibTeX has no untyped entries) and a ``key``.
    """
    db = _require_pybtex()
    if not reference.key:
        raise ValueError("reference needs a 'key' to become a BibTeX entry")
    if not reference.entry_type:
        raise ValueError(
            f"reference {reference.key!r} needs an 'entry_type' (e.g. 'article', 'book')"
        )
    persons = {
        role: [db.Person(name) for name in names]
        for role, names in reference.persons.items()
    }
    entry = db.Entry(
        reference.entry_type,
        fields={k: str(v) for k, v in reference.fields.items()},
        persons=persons,
    )
    return reference.key, entry


def entry_to_reference(key: str, entry: Any) -> Reference:
    """Convert a ``pybtex.Entry`` (under ``key``) into a :class:`~valuez.Reference`.

    The human-readable ``source`` is derived from the entry title (falling back
    to the citation key), so the resulting reference is usable everywhere a plain
    reference is.
    """
    fields = {k: str(v) for k, v in entry.fields.items()}
    persons = {role: [str(p) for p in plist] for role, plist in entry.persons.items()}
    source = fields.get("title") or key
    return Reference(
        source,
        key=key,
        entry_type=entry.type,
        fields=fields,
        persons=persons,
    )


def _slug_key(source: str) -> str:
    """A citation-key-friendly slug of a source string."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", source).strip("_").lower()
    return slug or "ref"


def _as_reference(item: Any) -> Optional[Reference]:
    """Extract a Reference from a Reference or any object with a ``.reference``."""
    if isinstance(item, Reference):
        return item
    ref = getattr(item, "reference", None)
    return ref if isinstance(ref, Reference) else None


class ReferenceRepository:
    """A keyed, de-duplicated collection of bibliographic sources.

    References are stored by their citation ``key``. Adding an identical entry
    twice is idempotent; adding a *different* entry under an existing key raises
    unless ``replace=True``. BibTeX import/export and formatting require the
    optional ``pybtex`` dependency.
    """

    def __init__(self, references: Iterable[Reference] = ()) -> None:
        self._by_key: Dict[str, Reference] = {}
        for ref in references:
            self.add(ref)

    # ------------------------------------------------------------------ #
    # Pure-Python collection API (no pybtex required)                    #
    # ------------------------------------------------------------------ #
    def add(self, reference: Reference, *, replace: bool = False) -> str:
        """Add a keyed reference; return its key.

        Idempotent for identical entries; raises on a conflicting key unless
        ``replace`` is set.
        """
        if not isinstance(reference, Reference):
            raise TypeError("ReferenceRepository stores Reference instances")
        if not reference.key:
            raise ValueError("a reference needs a 'key' to be stored in the repository")
        existing = self._by_key.get(reference.key)
        if existing is not None and not replace and existing != reference:
            raise ValueError(
                f"key {reference.key!r} already exists with different content "
                f"(pass replace=True to overwrite)"
            )
        self._by_key[reference.key] = reference
        return reference.key

    def add_all(self, references: Iterable[Reference], *, replace: bool = False) -> List[str]:
        return [self.add(r, replace=replace) for r in references]

    @classmethod
    def from_values(
        cls,
        values: Iterable[Any],
        *,
        include_unkeyed: bool = False,
        on_conflict: str = "first",
    ) -> "ReferenceRepository":
        """Collect the sources cited across an ontology into one repository.

        ``values`` may be :class:`~valuez.Reference` instances or any objects that
        carry a ``.reference`` (e.g. every :class:`~valuez.values.Value`), so this
        works directly on a :class:`~valuez.Reading` session's ``values()``, a
        list of stored objects, etc.

        Only references with a citation ``key`` are collected by default (those
        are the bibliographic *sources*); pass ``include_unkeyed=True`` to also
        gather passage-only references, synthesizing a key from their ``source``.
        ``on_conflict`` decides what happens when one key maps to two different
        references: ``"first"`` keeps the first seen (default), ``"replace"``
        keeps the last, and ``"raise"`` raises.
        """
        if on_conflict not in ("first", "replace", "raise"):
            raise ValueError("on_conflict must be 'first', 'replace', or 'raise'")
        repo = cls()
        for item in values:
            ref = _as_reference(item)
            if ref is None:
                continue
            key = ref.key
            if not key:
                if not include_unkeyed:
                    continue
                base = _slug_key(ref.source)
                key, n = base, 2
                while key in repo:
                    key, n = f"{base}_{n}", n + 1
                data = ref.to_dict()
                data.setdefault("bibtex", {})["key"] = key
                ref = Reference.from_dict(data)
            existing = repo.get(key)
            if existing is not None and existing != ref:
                if on_conflict == "raise":
                    raise ValueError(f"key {key!r} cited with conflicting references")
                if on_conflict == "first":
                    continue
            repo.add(ref, replace=True)
        return repo

    def get(self, key: str) -> Optional[Reference]:
        return self._by_key.get(key)

    def reference(self, key: str) -> Reference:
        """Return the source stored under ``key`` (raises if unknown).

        Attach the result to values so many of them share one keyed source.
        """
        try:
            return self._by_key[key]
        except KeyError:
            raise KeyError(f"no reference with key {key!r}") from None

    @property
    def references(self) -> List[Reference]:
        return list(self._by_key.values())

    def keys(self) -> List[str]:
        return list(self._by_key.keys())

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def __getitem__(self, key: str) -> Reference:
        return self.reference(key)

    def __len__(self) -> int:
        return len(self._by_key)

    def __iter__(self) -> Iterator[Reference]:
        return iter(self._by_key.values())

    def __repr__(self) -> str:
        return f"ReferenceRepository({len(self._by_key)} sources)"

    # ------------------------------------------------------------------ #
    # BibTeX I/O and formatting (require pybtex)                          #
    # ------------------------------------------------------------------ #
    def _bibliography_data(self) -> Any:
        """A ``pybtex.BibliographyData`` of all entries that have an entry_type."""
        db = _require_pybtex()
        entries = {}
        for ref in self._by_key.values():
            if not ref.entry_type:
                continue  # sources without a BibTeX type can't be serialized
            key, entry = reference_to_entry(ref)
            entries[key] = entry
        return db.BibliographyData(entries=entries)

    def import_bibtex(
        self,
        source: Union[str, Path],
        *,
        replace: bool = False,
    ) -> List[str]:
        """Import entries from a ``.bib`` file path or a BibTeX string.

        Returns the list of keys added. A path that exists on disk is read as a
        file; anything else is treated as literal BibTeX text.
        """
        db = _require_pybtex()
        text_or_path = source
        is_path = isinstance(source, Path) or (
            isinstance(source, str) and os.path.exists(source)
        )
        if is_path:
            data = db.parse_file(str(text_or_path))
        else:
            data = db.parse_string(str(text_or_path), "bibtex")
        added: List[str] = []
        for key, entry in data.entries.items():
            self.add(entry_to_reference(key, entry), replace=replace)
            added.append(key)
        return added

    def export_bibtex(self, path: Optional[Union[str, Path]] = None) -> str:
        """Serialize all typed sources to a BibTeX string (and optionally a file)."""
        text = self._bibliography_data().to_string("bibtex")
        if path is not None:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return text

    def format_bibliography(
        self,
        *,
        style: str = "plain",
        backend: str = "plaintext",
    ) -> Dict[str, str]:
        """Render each typed source to a formatted citation string.

        Returns a mapping ``{key: formatted_text}``. ``style`` is any installed
        ``pybtex`` formatting style (e.g. ``plain``, ``unsrt``, ``alpha``) and
        ``backend`` any output backend (``plaintext``, ``html``, ``latex``).
        """
        _require_pybtex()
        from pybtex.plugin import find_plugin

        style_obj = find_plugin("pybtex.style.formatting", style)()
        backend_obj = find_plugin("pybtex.backends", backend)()
        formatted = style_obj.format_bibliography(self._bibliography_data())
        return {entry.key: entry.text.render(backend_obj) for entry in formatted.entries}
