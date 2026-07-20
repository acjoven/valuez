"""Tests for BibTeX-backed references and the ReferenceRepository."""
import pytest

from valuez import Reference, ReferenceRepository, Scalar, Value, bibliography

pybtex = pytest.importorskip("pybtex")  # skip the pybtex-only tests without it


# --------------------------------------------------------------------------- #
# Reference: structured bibliographic fields (no pybtex needed)               #
# --------------------------------------------------------------------------- #
def test_reference_bib_fields_and_authors_shorthand():
    ref = Reference(
        "Critique of Pure Reason",
        key="kant1998",
        entry_type="book",
        fields={"title": "Critique of Pure Reason", "year": 1998},
        authors=["Kant, Immanuel", "Guyer, Paul"],
    )
    assert ref.key == "kant1998"
    assert ref.entry_type == "book"
    assert ref.fields["year"] == "1998"  # coerced to str
    assert ref.authors == ["Kant, Immanuel", "Guyer, Paul"]
    assert ref.persons["author"] == ref.authors
    assert ref.has_bibentry is True


def test_reference_without_bib_data_is_plain():
    ref = Reference("Some source")
    assert ref.has_bibentry is False
    assert "bibtex" not in ref.to_dict()


def test_reference_bib_dict_round_trip():
    ref = Reference(
        "Fundamentals of Heat and Mass Transfer",
        locator="Table A.1", confidence=0.9,
        key="incropera2007", entry_type="book",
        fields={"title": "Fundamentals of Heat and Mass Transfer", "year": "2007"},
        persons={"author": ["Incropera, Frank P."], "editor": ["Smith, Jane"]},
    )
    data = ref.to_dict()
    assert data["bibtex"]["key"] == "incropera2007"
    assert data["bibtex"]["persons"]["editor"] == ["Smith, Jane"]
    assert Reference.from_dict(data) == ref


def test_bib_reference_survives_value_serialization():
    ref = Reference("k source", key="k1", entry_type="misc",
                    fields={"note": "n"}, authors=["Doe, J."])
    s = Scalar(1.0, unit="m", reference=ref)
    restored = Value.from_dict(s.to_dict())
    assert restored.reference == ref
    assert restored.reference.key == "k1"


def test_reference_bib_validation():
    with pytest.raises(ValueError):
        Reference("s", key="")           # empty key
    with pytest.raises(ValueError):
        Reference("s", entry_type="")     # empty entry_type
    with pytest.raises(ValueError):
        Reference("s", fields={"": "x"})  # empty field name


# --------------------------------------------------------------------------- #
# ReferenceRepository: pure-Python collection semantics                       #
# --------------------------------------------------------------------------- #
def _kant() -> Reference:
    return Reference("Critique of Pure Reason", key="kant1998", entry_type="book",
                     fields={"title": "Critique of Pure Reason", "year": "1998",
                             "publisher": "Cambridge UP"},
                     authors=["Kant, Immanuel"])


def test_repository_add_get_and_membership():
    repo = ReferenceRepository([_kant()])
    assert len(repo) == 1
    assert "kant1998" in repo
    assert repo.reference("kant1998").source == "Critique of Pure Reason"
    assert repo["kant1998"] is repo.get("kant1998")
    assert [r.key for r in repo] == ["kant1998"]


def test_repository_requires_key():
    repo = ReferenceRepository()
    with pytest.raises(ValueError):
        repo.add(Reference("no key here"))


def test_repository_dedup_idempotent_and_conflict():
    repo = ReferenceRepository()
    repo.add(_kant())
    repo.add(_kant())  # identical -> idempotent
    assert len(repo) == 1
    with pytest.raises(ValueError):
        repo.add(Reference("other", key="kant1998", entry_type="misc"))
    repo.add(Reference("other", key="kant1998", entry_type="misc"), replace=True)
    assert repo.reference("kant1998").entry_type == "misc"


def test_repository_unknown_key_raises():
    repo = ReferenceRepository()
    with pytest.raises(KeyError):
        repo.reference("nope")


# --------------------------------------------------------------------------- #
# BibTeX conversion, import/export, formatting (pybtex)                        #
# --------------------------------------------------------------------------- #
def test_reference_entry_conversion_round_trip():
    ref = _kant()
    key, entry = bibliography.reference_to_entry(ref)
    assert key == "kant1998"
    assert entry.type == "book"
    back = bibliography.entry_to_reference(key, entry)
    assert back.key == "kant1998"
    assert back.entry_type == "book"
    assert back.fields["year"] == "1998"
    assert back.authors == ["Kant, Immanuel"]


def test_reference_to_entry_requires_type():
    with pytest.raises(ValueError):
        bibliography.reference_to_entry(Reference("s", key="k1"))  # no entry_type


def test_import_bibtex_from_string():
    repo = ReferenceRepository()
    added = repo.import_bibtex(
        "@article{i2007, author={Incropera, Frank P.}, "
        "title={Heat Transfer}, year={2007}, journal={Wiley}}"
    )
    assert added == ["i2007"]
    ref = repo.reference("i2007")
    assert ref.entry_type == "article"
    assert ref.source == "Heat Transfer"  # derived from title
    assert ref.authors == ["Incropera, Frank P."]


def test_export_bibtex_round_trips_through_reimport(tmp_path):
    repo = ReferenceRepository([_kant()])
    path = tmp_path / "refs.bib"
    text = repo.export_bibtex(path)
    assert path.read_text() == text
    assert "@book{kant1998" in text

    repo2 = ReferenceRepository()
    repo2.import_bibtex(path)
    assert repo2.reference("kant1998").fields["publisher"] == "Cambridge UP"


def test_export_skips_sources_without_entry_type():
    repo = ReferenceRepository()
    repo.add(Reference("plain note", key="note1"))  # no entry_type
    repo.add(_kant())
    text = repo.export_bibtex()
    assert "kant1998" in text
    assert "note1" not in text


def test_format_bibliography_plain():
    repo = ReferenceRepository([_kant()])
    formatted = repo.format_bibliography()
    assert "kant1998" in formatted
    text = formatted["kant1998"]
    assert "Kant" in text and "1998" in text


def test_format_bibliography_html_backend():
    repo = ReferenceRepository([_kant()])
    formatted = repo.format_bibliography(style="unsrt", backend="html")
    assert "kant1998" in formatted


# --------------------------------------------------------------------------- #
# Collection helper: from_values + Reading/ValueRepository wrappers            #
# --------------------------------------------------------------------------- #
def _incropera() -> Reference:
    return Reference("Fundamentals of Heat and Mass Transfer", key="incropera2007",
                     entry_type="book", fields={"year": "2007"})


def test_from_values_collects_keyed_sources_and_dedups():
    incr = _incropera()
    values = [
        Scalar(2.0, unit="W/m^2/K", reference=incr),
        Scalar(25.0, unit="W/m^2/K", reference=incr),  # same shared source
        Scalar(1.0, reference=_kant()),
        Scalar(3.0),  # ungrounded -> ignored
    ]
    bib = ReferenceRepository.from_values(values)
    assert sorted(bib.keys()) == ["incropera2007", "kant1998"]


def test_from_values_accepts_bare_references():
    bib = ReferenceRepository.from_values([_kant(), _incropera()])
    assert len(bib) == 2


def test_from_values_skips_unkeyed_by_default_and_can_include():
    passage = Reference("Some Book", locator="p.12")  # no key
    values = [Scalar(1.0, reference=passage), Scalar(2.0, reference=_kant())]
    assert ReferenceRepository.from_values(values).keys() == ["kant1998"]
    both = ReferenceRepository.from_values(values, include_unkeyed=True)
    assert "kant1998" in both
    assert "some_book" in both  # synthesized from the source string


def test_from_values_conflict_policies():
    a = Reference("X", key="dup", entry_type="misc", fields={"year": "2000"})
    b = Reference("Y", key="dup", entry_type="misc", fields={"year": "2001"})
    assert ReferenceRepository.from_values([a, b]).reference("dup").fields["year"] == "2000"
    replaced = ReferenceRepository.from_values([a, b], on_conflict="replace")
    assert replaced.reference("dup").fields["year"] == "2001"
    with pytest.raises(ValueError):
        ReferenceRepository.from_values([a, b], on_conflict="raise")
    with pytest.raises(ValueError):
        ReferenceRepository.from_values([a], on_conflict="bogus")


def test_reading_bibliography_wrapper():
    from valuez import Reading, Vocabulary

    book = Reading(source="CPR", predicates=Vocabulary("p", ["is-a"]))
    with book.cite(_kant()):
        book.universal("Space")
        book.universal("Intuition")
        book.relate("Space", "is-a", "Intuition")
    bib = book.bibliography()
    assert bib.keys() == ["kant1998"]


def test_value_repository_bibliography_wrapper(tmp_path):
    from valuez.repository import ValueRepository

    incr = _incropera()
    repo = ValueRepository(data_dir=tmp_path / "store")
    repo.add_values([Scalar(2.0, reference=incr), Scalar(1.0, reference=_kant())])
    bib = repo.bibliography()
    assert sorted(bib.keys()) == ["incropera2007", "kant1998"]
    assert "@book{kant1998" in bib.export_bibtex()
