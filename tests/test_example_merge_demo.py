"""Guard for examples/merge_demo.py and the two small maps it builds."""
import importlib.util
import json
from pathlib import Path

from valuez import merge_ontologies

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGIES = ROOT / "ontologies"

_SPEC = importlib.util.spec_from_file_location("merge_demo", ROOT / "examples" / "merge_demo.py")
demo = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(demo)

MAPS = [ONTOLOGIES / "thermodynamics.json", ONTOLOGIES / "kinetic_theory.json"]
JOINS = {"InternalEnergy", "Pressure", "Temperature", "Volume"}


def test_both_maps_build_and_validate():
    thermo, kinetic = demo.build_thermodynamics(), demo.build_kinetic_theory()
    assert thermo.validate() == [] and kinetic.validate() == []
    assert (thermo.stats()["concepts"], thermo.stats()["relations"]) == (12, 17)
    assert (kinetic.stats()["concepts"], kinetic.stats()["relations"]) == (9, 8)
    assert all(v.is_grounded() for v in thermo.values() + kinetic.values())


def test_committed_maps_match_the_builder(tmp_path):
    fresh = demo.write_maps(tmp_path)
    for path in fresh:
        assert path.read_bytes() == (ONTOLOGIES / path.name).read_bytes(), (
            f"ontologies/{path.name} is stale; re-run examples/merge_demo.py"
        )


def test_ids_are_disjoint_between_the_maps():
    thermo, kinetic = (
        {d["id"] for d in json.loads(path.read_text(encoding="utf-8"))} for path in MAPS
    )
    assert all(i.startswith("td_") for i in thermo)
    assert all(i.startswith("kt_") for i in kinetic)


def test_merge_joins_the_four_shared_names():
    report = merge_ontologies(MAPS).report
    assert report.sources == ["thermodynamics", "kinetic_theory"]
    assert set(report.join_points) == JOINS
    assert report.dangling_edges == [] and report.type_conflicts == {}
    assert (report.input_total, report.output_total) == (48, 42)


def test_three_joins_disagree_on_definition_and_one_does_not():
    conflicts = merge_ontologies(MAPS).report.field_conflicts
    differing = {name for name, fields in conflicts.items() if "definition" in fields}
    assert differing == {"InternalEnergy", "Pressure", "Temperature"}
    assert "definition" not in conflicts.get("Volume", {})


def test_first_source_definition_wins_by_default():
    result = merge_ontologies(MAPS)
    temperature = next(d for d in result.documents if d.get("name") == "Temperature")
    assert "reversible engine" in temperature["definition"]
    flipped = merge_ontologies(MAPS, on_conflict="last")
    temperature = next(d for d in flipped.documents if d.get("name") == "Temperature")
    assert "mean kinetic energy" in temperature["definition"]


def test_edges_asserted_by_both_maps_collapse():
    report = merge_ontologies(MAPS).report
    shared = {key[1:4] for key, _ in report.shared_edges}
    assert shared == {
        ("Pressure", "depends-on", "Temperature"),
        ("Pressure", "depends-on", "Volume"),
    }
    assert (report.edges_in, report.edges_out, report.edges_deduped) == (25, 23, 2)


def test_crossings_exist_only_in_the_merged_map():
    found = merge_ontologies(MAPS).discover(cutoff=2, limit=0)
    paths = {c.path.describe() for c in found.between("thermodynamics", "kinetic_theory")}
    assert paths == {
        "Entropy -depends-on-> Temperature -measures-> MeanKineticEnergy",
        "FirstLaw -governs-> InternalEnergy -depends-on-> MeanKineticEnergy",
        "Heat -changes-> InternalEnergy -depends-on-> MeanKineticEnergy",
        "ReversibleEngine -defines-> Temperature -measures-> MeanKineticEnergy",
        "Work -changes-> InternalEnergy -depends-on-> MeanKineticEnergy",
        "Work -depends-on-> Pressure <-causes- MolecularCollision",
    }
    assert found.total == 12
    for single in (demo.build_thermodynamics(), demo.build_kinetic_theory()):
        graph = single.graph()
        assert "ReversibleEngine" not in graph or "MeanKineticEnergy" not in graph


def test_alias_adds_a_join_and_a_crossing():
    aligned = merge_ontologies(MAPS, aliases=demo.ALIASES)
    assert set(aligned.report.join_points) == JOINS | {"IdealGas"}
    assert aligned.report.aliases_applied == {"IdealGas": ["IdealGas", "PerfectGas"]}
    via = aligned.discover(cutoff=2, limit=0).via("IdealGas")
    assert "ReversibleEngine -uses-> IdealGas -is-a-> Gas" in {c.path.describe() for c in via}


def test_demo_runs_without_touching_the_committed_maps(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo, "ONTOLOGIES", tmp_path / "maps")
    monkeypatch.setenv("VALUEZ_EXAMPLE_OUT", str(tmp_path / "out"))
    demo.main()
    out = capsys.readouterr().out
    assert "Join points (common nodes joined): 4" in out
    assert "ReversibleEngine -defines-> Temperature -measures-> MeanKineticEnergy" in out
    assert "join points 4 -> 5" in out
    assert (tmp_path / "out" / "gas_universe.json").exists()
    assert (tmp_path / "maps" / "thermodynamics.json").exists()
