"""Configuration acceptance tests derived from EverlongSTK spec v0.2."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from everlong_stk.configuration import (
    EARTH_EQUATORIAL_RADIUS_M,
    ConfigurationError,
    load_configuration,
    resolved_to_dict,
    save_configuration,
    validate_configuration,
)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "generic_cubesat.json"


@pytest.fixture
def raw():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def mutate(raw, *path, value):
    obj = copy.deepcopy(raw)
    cursor = obj
    for part in path[:-1]:
        cursor = cursor[part]
    cursor[path[-1]] = value
    return obj


def check_invalid(raw, *path, error):
    with pytest.raises(ConfigurationError, match=error):
        validate_configuration(mutate(raw, *path, value=None))


def test_example_is_valid_and_representative():
    config = load_configuration(EXAMPLE)
    assert config.schema_version == "0.2"
    assert len(config.modes) == 4
    assert {m.id for m in config.modes} == {"a", "b", "c", "d"}
    assert len(config.components) == 8
    assert config.defaults.initial_mode_id == "a"
    assert config.control.type == "blocks"
    assert config.components[2].producer.destination_queue_id == "raw"
    assert config.components[3].processor.output_input_ratio.value == 0.25
    assert config.components[4].mode_values["d"].downlink_bps.value == 1_000_000
    assert config.components[5].mode_values["b"].generation_w.value == 6
    assert config.components[6].battery.initial_energy_wh.value == 32
    assert config.components[7].storage.usable_bytes.value == 1_000_000_000
    assert config.ground_stations[0].minimum_elevation_deg.value == 10
    assert config.control.rules[1].condition.children[1].queue_id == "processed"


def test_exact_round_trip_input_and_resolved_data(tmp_path, raw):
    before = copy.deepcopy(raw)
    config = validate_configuration(raw)
    assert raw == before
    filename = tmp_path / "reloaded.json"
    save_configuration(config, filename)
    assert json.loads(filename.read_text()) == before
    reloaded = load_configuration(filename)
    assert reloaded == config
    assert resolved_to_dict(reloaded) == resolved_to_dict(config)
    assert "original" not in resolved_to_dict(config)


def test_save_raw_configuration_and_unicode_provenance(tmp_path, raw):
    raw["project"]["description"] = "Camera résumé — test źródło"
    raw["components"][0]["mass_kg"]["source"] = "https://example.invalid/bus"
    raw["components"][0]["mass_kg"]["lower_bound"] = 0.4
    raw["components"][0]["mass_kg"]["upper_bound"] = 0.6
    path = tmp_path / "unicode.json"
    save_configuration(raw, path)
    saved = load_configuration(path)
    assert saved.original == raw
    assert saved.components[0].mass_kg.source == "https://example.invalid/bus"
    assert saved.components[0].mass_kg.lower_bound == 0.4
    assert saved.components[0].mass_kg.upper_bound == 0.6


def test_explicit_zero_is_not_a_default(raw):
    config = validate_configuration(raw)
    camera_a = config.components[2].mode_values["a"]
    camera_c = config.components[2].mode_values["c"]
    assert camera_a.data_generation_bytes_per_s.value == 0
    assert camera_a.data_generation_bytes_per_s.is_default is False
    assert camera_c.data_generation_bytes_per_s.value == 0
    assert camera_c.data_generation_bytes_per_s.is_default is True
    assert "components[2].mode_values.c.data_generation_bytes_per_s" in config.defaults_applied
    assert "components[2].mode_values.a.data_generation_bytes_per_s" not in config.defaults_applied
    assert config.components[7].storage.initial_queue_bytes["raw"].value == 0
    assert config.components[7].storage.initial_queue_bytes["raw"].is_default is False


def test_missing_entire_mode_entry_zeroes_independently(raw):
    del raw["components"][2]["mode_values"]["b"]
    config = validate_configuration(raw)
    camera = config.components[2].mode_values
    assert camera["b"].active is False
    assert camera["b"].active_power_w.value == 0
    assert camera["b"].data_generation_bytes_per_s.value == 0
    assert camera["b"].data_generation_bytes_per_s.is_default
    assert camera["c"].idle_power_w.value == 0.1
    assert "components[2].mode_values.b" in config.defaults_applied


def test_circular_orbit_resolves_advanced_elements(raw):
    orbit = validate_configuration(raw).orbit
    assert orbit.semi_major_axis_m.value == EARTH_EQUATORIAL_RADIUS_M + 550_000
    assert orbit.eccentricity.value == 0
    assert orbit.eccentricity.is_default
    assert orbit.epoch_utc == "2027-01-01T00:00:00Z"
    assert orbit.frame == "ECI_J2000"


def test_advanced_elliptic_orbit(raw):
    del raw["orbit"]["circular_altitude_m"]
    raw["orbit"]["semi_major_axis_m"] = {"value": 7_100_000, "unit": "m"}
    raw["orbit"]["eccentricity"] = {"value": 0.01, "unit": "1"}
    orbit = validate_configuration(raw).orbit
    assert orbit.semi_major_axis_m.value == 7_100_000
    assert orbit.eccentricity.value == 0.01
    assert not orbit.eccentricity.is_default


@pytest.mark.parametrize(
    ("path", "replacement", "error"),
    [
        (("orbit", "inclination_deg"), None, "orbit.inclination_deg"),
        (("orbit", "circular_altitude_m"), {"value": 550000, "unit": "km"}, "canonical unit"),
        (("simulation", "duration_s"), {"value": 0, "unit": "s"}, "must be > 0"),
        (("simulation", "duration_s"), {"value": -1, "unit": "s"}, "must be > 0"),
        (("simulation", "duration_s"), {"value": float("inf"), "unit": "s"}, "finite"),
        (("simulation", "duration_s"), {"value": True, "unit": "s"}, "finite"),
        (("simulation", "output_interval_s"), {"value": 10, "unit": "s"}, "cannot be less"),
        (("simulation", "epoch_utc"), "2027-01-01T00:00:00+02:00", "UTC"),
        (("orbit", "inclination_deg"), {"value": 190, "unit": "deg"}, "<= 180"),
        (("orbit", "circular_altitude_m"), {"value": -1, "unit": "m"}, ">= 0"),
        (("defaults", "initial_mode_id"), "invalid", "unknown reference"),
        (("components", 2, "capabilities", "producer", "destination_queue_id"), "missing", "unknown reference"),
        (("components", 4, "capabilities", "radio", "supported_station_ids"), ["missing"], "unknown reference"),
        (("ground_stations", 0, "supported_radio_ids"), ["missing"], "unknown reference"),
        (("components", 2, "mode_values", "a", "idle_power_w"), {"value": -0.1, "unit": "W"}, ">= 0"),
        (("components", 3, "capabilities", "processor", "output_input_ratio"), {"value": -0.25, "unit": "1"}, ">= 0"),
        (("components", 6, "capabilities", "battery", "charge_efficiency"), {"value": 0, "unit": "1"}, "> 0"),
        (("components", 6, "capabilities", "battery", "discharge_efficiency"), {"value": 1.1, "unit": "1"}, "<= 1"),
        (("components", 6, "capabilities", "battery", "initial_energy_wh"), {"value": 41, "unit": "Wh"}, "exceeds capacity"),
        (("control", "rules", 0, "actions", "mode_id"), "unknown", "unknown reference"),
        (("control", "rules", 1, "condition", "all", 1, "queue_id"), "unknown", "unknown reference"),
        (("control", "rules", 0, "condition", "value"), {"value": 20, "unit": "W"}, "canonical unit"),
    ],
)
def test_invalid_inputs_have_paths(raw, path, replacement, error):
    with pytest.raises(ConfigurationError, match=error):
        validate_configuration(mutate(raw, *path, value=replacement))


def test_missing_required_top_level_geometry(raw):
    del raw["orbit"]["inclination_deg"]
    with pytest.raises(ConfigurationError, match="orbit.inclination_deg: required"):
        validate_configuration(raw)


def test_unknown_fields_rejected_not_dropped(raw):
    raw["components"][2]["caps_typo"] = 10
    with pytest.raises(ConfigurationError, match="unknown field"):
        validate_configuration(raw)


def test_duplicate_ids_and_duplicate_json_keys(raw, tmp_path):
    raw["modes"][1]["id"] = "a"
    with pytest.raises(ConfigurationError, match="duplicate ID"):
        validate_configuration(raw)
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": "0.2", "schema_version": "0.2"}')
    with pytest.raises(ConfigurationError, match="duplicate object key"):
        load_configuration(path)


def test_nonfinite_json_constants_are_rejected(tmp_path):
    path = tmp_path / "nan.json"
    path.write_text('{"duration": NaN}')
    with pytest.raises(ConfigurationError, match="nonfinite"):
        load_configuration(path)


def test_invalid_parameter_bounds_and_certainty(raw):
    raw["components"][0]["mass_kg"].update({"lower_bound": 0.6})
    with pytest.raises(ConfigurationError, match="lower_bound exceeds value"):
        validate_configuration(raw)
    raw["components"][0]["mass_kg"].pop("lower_bound")
    raw["components"][0]["mass_kg"]["certainty"] = "trustworthy"
    with pytest.raises(ConfigurationError, match="certainty"):
        validate_configuration(raw)


def test_total_initial_queue_volume_cannot_exceed_capacity(raw):
    raw["components"][7]["capabilities"]["storage"]["initial_queue_bytes"]["raw"]["value"] = 1_000_000_001
    with pytest.raises(ConfigurationError, match="exceeds usable_bytes"):
        validate_configuration(raw)


def test_mode_rename_preserves_references(raw):
    raw["modes"][1]["label"] = "New label: photography"
    config = validate_configuration(raw)
    assert config.modes[1].label == "New label: photography"
    assert config.control.rules[3].actions.mode_id == "b"
    assert config.components[2].mode_values["b"].data_generation_bytes_per_s.value == 500_000


def test_bad_mode_key_does_not_copy_another_mode(raw):
    raw["components"][2]["mode_values"]["unknown"] = {}
    with pytest.raises(ConfigurationError, match="unknown field"):
        validate_configuration(raw)


def test_missing_capability_for_mode_value_is_invalid(raw):
    raw["components"][5]["mode_values"]["a"]["downlink_bps"] = {"value": 1, "unit": "bit/s"}
    with pytest.raises(ConfigurationError, match="requires radio capability"):
        validate_configuration(raw)


def test_only_one_physical_storage_and_battery(raw):
    raw["components"].append(copy.deepcopy(raw["components"][7]))
    raw["components"][-1]["id"] = "storage2"
    with pytest.raises(ConfigurationError, match="at most one storage"):
        validate_configuration(raw)


def test_schedule_nonoverlap_and_reference_validation(raw):
    v = lambda value: {"value": value, "unit": "s"}  # noqa: E731
    raw["control"] = {
        "type": "schedule",
        "intervals": [
            {"start_elapsed_s": v(0), "end_elapsed_s": v(30), "actions": {"mode_id": "a"}},
            {"start_elapsed_s": v(30), "end_elapsed_s": v(60), "actions": {"mode_id": "d"}},
        ],
        "fallback": {"mode_id": "a"},
    }
    assert validate_configuration(raw).control.intervals[1].start_elapsed_s.value == 30
    raw["control"]["intervals"][1]["start_elapsed_s"] = v(29)
    with pytest.raises(ConfigurationError, match="intervals overlap"):
        validate_configuration(raw)


def test_schedule_utc_overlap_and_invalid_deletions(raw):
    raw["control"] = {
        "type": "schedule",
        "intervals": [
            {"start_utc": "2027-01-01T00:00:00Z", "end_utc": "2027-01-01T01:00:00Z",
             "actions": {"delete_requests": [{"queue_id": "raw", "bytes": {"value": 0, "unit": "byte"}}]}},
            {"start_utc": "2027-01-01T00:30:00Z", "end_utc": "2027-01-01T02:00:00Z",
             "actions": {"mode_id": "b"}},
        ],
        "fallback": {},
    }
    with pytest.raises(ConfigurationError, match="intervals overlap"):
        validate_configuration(raw)
    raw["control"]["intervals"][1]["start_utc"] = "2027-01-01T01:00:00Z"
    assert validate_configuration(raw).control.intervals[0].actions.delete_requests[0].bytes.value == 0
    raw["control"]["intervals"][0]["actions"]["delete_requests"][0]["bytes"]["value"] = -10
    with pytest.raises(ConfigurationError, match=">= 0"):
        validate_configuration(raw)


def test_unsupported_control_type_and_invalid_rule(raw):
    raw["control"]["type"] = "something"
    with pytest.raises(ConfigurationError, match="unsupported controller"):
        validate_configuration(raw)
    raw["control"]["type"] = "blocks"
    raw["control"]["rules"][0]["condition"] = {"field": "battery_percent", "op": "bad", "value": {"value": 20, "unit": "%"}}
    with pytest.raises(ConfigurationError, match="invalid comparison"):
        validate_configuration(raw)


def test_python_control_can_preserve_script_source(raw, tmp_path):
    raw["control"] = {"type": "python", "script_source": "def decide_actions(status):\n    return Actions(mode_id='a')\n"}
    project = validate_configuration(raw)
    assert project.control.script_source == raw["control"]["script_source"]
    path = tmp_path / "python.json"
    save_configuration(project, path)
    assert load_configuration(path).control.script_source == project.control.script_source


def test_numeric_type_in_control_rule(raw):
    raw["control"]["rules"][0]["condition"]["value"] = 20
    with pytest.raises(ConfigurationError, match="expected object"):
        validate_configuration(raw)


def test_missing_defaulted_parameters_are_tracked(raw):
    raw["components"][2]["mode_values"]["c"].pop("idle_power_w")
    result = validate_configuration(raw)
    camera = result.components[2].mode_values["c"]
    assert camera.idle_power_w.value == 0
    assert camera.idle_power_w.is_default
    assert "components[2].mode_values.c.idle_power_w" in result.defaults_applied


def test_explicit_empty_stations_are_allowed(raw):
    raw["ground_stations"] = []
    raw["components"][4]["capabilities"]["radio"]["supported_station_ids"] = []
    result = validate_configuration(raw)
    assert result.ground_stations == ()


def test_invalid_queue_default_reference(raw):
    raw["defaults"]["default_downlink_queue_id"] = "not_a_queue"
    with pytest.raises(ConfigurationError, match="unknown reference"):
        validate_configuration(raw)


def test_unrecognized_schema_versions_rejected(raw):
    raw["schema_version"] = "0.3"
    with pytest.raises(ConfigurationError, match="schema_version"):
        validate_configuration(raw)


def test_per_mode_current_draws_are_unit_checked_and_round_trip(tmp_path, raw):
    raw["components"][0]["mode_values"]["a"]["active_current_a"] = {
        "value": 0.25, "unit": "A", "certainty": "tested", "source": "bench test"
    }
    raw["components"][0]["mode_values"]["a"]["idle_current_a"] = {
        "value": 0, "unit": "A", "certainty": "specified"
    }
    result = validate_configuration(raw)
    active = result.components[0].mode_values["a"].active_current_a
    assert active.value == 0.25 and active.certainty == "tested"
    assert result.components[0].mode_values["a"].idle_current_a.value == 0
    assert not result.components[0].mode_values["a"].idle_current_a.is_default
    assert result.components[0].mode_values["b"].active_current_a.is_default
    path = tmp_path / "with_current.json"
    save_configuration(result, path)
    assert load_configuration(path).original == raw
    raw["components"][0]["mode_values"]["a"]["active_current_a"]["unit"] = "mA"
    with pytest.raises(ConfigurationError, match="canonical unit"):
        validate_configuration(raw)


def test_committed_state_snapshot_queue_occupancy_is_read_only():
    from everlong_stk.models import SatelliteState

    original = {"raw": 12.0}
    state = SatelliteState("2027-01-01T00:00:00Z", 0, "a", "sun", 32.0, original)
    original["raw"] = 500.0
    assert state.queue_bytes["raw"] == 12.0
    with pytest.raises(TypeError):
        state.queue_bytes["raw"] = 1.0
