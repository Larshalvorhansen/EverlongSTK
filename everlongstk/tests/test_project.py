"""Task 001 public API acceptance cases."""

import copy
import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from everlong_stk.configuration import (
    ConfigurationError,
    export_component_table,
    load_project,
    resolve_project,
    save_project,
    validate_project,
)
from everlong_stk.models import Parameter

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/generic_cubesat.json"


@pytest.fixture
def raw():
    return json.loads(EXAMPLE.read_text())


def test_roundtrip_and_defaults(raw, tmp_path):
    original = copy.deepcopy(raw)
    config = resolve_project(raw)
    assert validate_project(config) == ()
    assert raw == original
    path = tmp_path / "project.json"
    save_project(path, config)
    assert json.loads(path.read_text()) == original
    assert load_project(path) == config
    assert [s.name for s in config.states] == [
        "Idle", "Capturing data", "Transmit/receive", "Survival"
    ]
    assert config.components[6].battery.capacity_wh.value == 40
    assert config.orbit.inclination_deg.value == 97.5


@pytest.mark.parametrize("field", ["current_a", "data_generation_bytes_per_s"])
def test_required_values_in_every_state(raw, field):
    del raw["components"][2]["mode_values"]["c"][field]
    issue, = validate_project(raw)
    assert issue.path == f"components[2].mode_values.c.{field}"
    assert "required" in issue.message


def test_added_state_requires_component_inputs(raw):
    raw["states"].append({"id": "new", "label": "Additional state"})
    assert "mode_values.new" in validate_project(raw)[0].path


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_data_rates(raw, value):
    raw["components"][2]["mode_values"]["b"]["data_generation_bytes_per_s"]["value"] = value
    assert validate_project(raw)[0].severity == "error"


def test_signed_current_and_bus_conversion(raw):
    # Independently calculated: 5 V * -1.2 A supplies 6 W; +0.4 A requests 2 W.
    raw["components"][5]["mode_values"]["a"]["current_a"]["value"] = -1.2
    raw["components"][0]["mode_values"]["a"]["current_a"]["value"] = 0.4
    config = resolve_project(raw)
    generator = config.components[5].mode_values["a"]
    load = config.components[0].mode_values["a"]
    assert (generator.nominal_generation_w, generator.nominal_load_w) == (6, 0)
    assert (load.nominal_generation_w, load.nominal_load_w) == (0, 2)
    raw["components"][0]["mode_values"]["a"]["current_a"]["value"] = -0.4
    assert "requires generator" in validate_project(raw)[0].message


@pytest.mark.parametrize("value,unit", [(0, "V"), (-5, "V"), (5, "mV"), (True, "V")])
def test_bus_validation(raw, value, unit):
    raw["electrical_bus"]["voltage_v"] = {"value": value, "unit": unit}
    assert validate_project(raw)


@pytest.mark.parametrize("capability", ["battery", "storage"])
@pytest.mark.parametrize("count", [0, 2])
def test_exactly_one_physical_resource(raw, capability, count):
    component = next(c for c in raw["components"] if capability in c["capabilities"])
    if count == 0:
        raw["components"].remove(component)
    else:
        duplicate = copy.deepcopy(component)
        duplicate["id"] += "_second"
        raw["components"].append(duplicate)
    assert f"exactly one {capability}" in validate_project(raw)[0].message


def test_transition_validation(raw):
    bad = copy.deepcopy(raw)
    bad["transitions"][0]["target_state_id"] = "missing"
    assert validate_project(bad)[0].path == "transitions[0].target_state_id"
    bad = copy.deepcopy(raw)
    bad["transitions"].append(copy.deepcopy(bad["transitions"][0]))
    assert "duplicate ID" in validate_project(bad)[0].message
    raw["transitions"][0]["minimum_dwell_seconds"] = {"value": -1, "unit": "s"}
    assert "minimum_dwell_seconds" in validate_project(raw)[0].path


def test_nonproducer_cannot_generate(raw):
    raw["components"][0]["mode_values"]["a"]["data_generation_bytes_per_s"] = {
        "value": 0, "unit": "byte/s"
    }
    assert "requires producer" in validate_project(raw)[0].message


def test_csv_units_values_escaping_and_stable_headers(raw, tmp_path):
    raw["components"][0]["name"] = 'Bus, "engineering"\nunit'
    path = tmp_path / "components.csv"
    export_component_table(resolve_project(raw), path)
    with path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 8
    assert rows[0]["row_number"] == "1"
    assert rows[0]["name"] == raw["components"][0]["name"]
    assert rows[5]["state[a].current_A"] == "-2.4"
    assert rows[2]["state[b].data_generation_bytes_per_s"] == "500000"
    assert rows[6]["battery_capacity_Wh"] == "40"
    assert rows[7]["storage_capacity_bytes"] == "1000000000"
    assert rows[4]["state[c].downlink_bits_per_s"] == "1000000"
    assert "station_1:10" in rows[4]["station_minimum_elevation_deg"]
    original_header = tuple(rows[0])
    raw["states"][0]["label"] = "Renamed, idle"
    export_component_table(resolve_project(raw), path)
    with path.open(newline="") as stream:
        renamed = list(csv.DictReader(stream))
    assert tuple(renamed[0]) == original_header
    assert renamed[0]["state[a].label"] == "Renamed, idle"


def test_typed_edits_are_saved_and_revalidated(tmp_path):
    config = load_project(EXAMPLE)
    changed = replace(config, project=replace(config.project, title="Edited"))
    path = tmp_path / "edited.json"
    save_project(path, changed)
    assert load_project(path).project.title == "Edited"
    assert load_project(path).transitions == config.transitions
    invalid = replace(config, electrical_bus_voltage_v=Parameter(-5, "V"))
    assert validate_project(invalid)
    with pytest.raises(ConfigurationError):
        save_project(path, invalid)
    assert load_project(path).project.title == "Edited"


def test_unrelated_edit_preserves_original_provenance_and_omissions(raw, tmp_path):
    original = copy.deepcopy(raw)
    config = resolve_project(raw)
    config = replace(config, project=replace(config.project, title="New title"))
    target = tmp_path / "changed.json"
    save_project(target, config)
    expected = copy.deepcopy(original)
    expected["project"]["title"] = "New title"
    assert json.loads(target.read_text()) == expected


def test_changing_orbit_size_switches_to_explicit_elements(tmp_path):
    config = load_project(EXAMPLE)
    orbit = replace(config.orbit, semi_major_axis_m=Parameter(7_100_000, "m"))
    path = tmp_path / "orbit.json"
    save_project(path, replace(config, orbit=orbit))
    document = json.loads(path.read_text())
    assert "circular_altitude_m" not in document["orbit"]
    assert load_project(path).orbit.semi_major_axis_m.value == 7_100_000


def test_disabled_generator_rejects_negative_current(raw):
    raw["components"][5]["capabilities"]["generator"]["enabled"] = False
    assert "requires generator" in validate_project(raw)[0].message


@pytest.mark.parametrize("value", [0, -1])
def test_invalid_storage_capacity(raw, value):
    raw["components"][7]["capabilities"]["storage"]["usable_bytes"]["value"] = value
    assert "usable_bytes" in validate_project(raw)[0].path
