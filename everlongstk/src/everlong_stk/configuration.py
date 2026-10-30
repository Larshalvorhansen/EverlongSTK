"""Strict, lossless JSON project I/O and explicit default resolution.

Canonical units are exact strings; no implicit unit conversions are performed.
Missing optional operational inputs default to zero independently for *each*
mode, rather than inheriting values from an adjacent mode.  ``original`` is
kept unchanged for lossless saves, while ``resolved_to_dict`` exposes every
applied default and the derived circular-orbit elements.
"""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from everlong_stk.models import (
    Actions,
    AvailabilityInterval,
    BatteryCapability,
    BlockRule,
    Component,
    Condition,
    ControlConfig,
    DataQueue,
    Defaults,
    DeleteRequest,
    GeneratorCapability,
    GroundStation,
    LoadCapability,
    Mode,
    ModeValues,
    OrbitalElements,
    Parameter,
    ProcessorCapability,
    ProducerCapability,
    ProjectInfo,
    RadioCapability,
    ResolvedConfiguration,
    ScheduleInterval,
    SimulationConfig,
    StorageCapability,
)

SCHEMA_VERSION = "0.2"
# WGS-84 equatorial radius, used only to resolve the convenience circular form.
EARTH_EQUATORIAL_RADIUS_M = 6_378_137.0
CERTAINTIES = {"guesstimate", "calculated_estimate", "specified", "tested"}
POINTINGS = {"sun", "nadir", "ground_station", "inertial"}
_ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_MISSING = object()


class ConfigurationError(ValueError):
    """Invalid configuration, with a JSON-style path to the affected input."""


class _Reader:
    def __init__(self) -> None:
        self.defaults_applied: list[str] = []

    def default(self, path: str) -> None:
        self.defaults_applied.append(path)

    def mapping(self, obj: Any, path: str, allowed: set[str]) -> dict[str, Any]:
        if not isinstance(obj, dict):
            raise ConfigurationError(f"{path}: expected object")
        unknown = set(obj) - allowed
        if unknown:
            raise ConfigurationError(f"{path}: unknown field(s): {', '.join(sorted(unknown))}")
        return obj

    def required(self, obj: dict[str, Any], key: str, path: str) -> Any:
        if key not in obj:
            raise ConfigurationError(f"{path}.{key}: required field missing")
        return obj[key]

    def optional(self, obj: dict[str, Any], key: str, default: Any, path: str) -> Any:
        if key not in obj:
            self.default(f"{path}.{key}")
            return default
        return obj[key]

    def string(self, obj: Any, path: str, *, nonempty: bool = True) -> str:
        if not isinstance(obj, str) or (nonempty and not obj.strip()):
            raise ConfigurationError(f"{path}: expected {'nonempty ' if nonempty else ''}string")
        return obj

    def ident(self, obj: Any, path: str) -> str:
        value = self.string(obj, path)
        if not _ID_PATTERN.fullmatch(value):
            raise ConfigurationError(f"{path}: expected stable ID [A-Za-z][A-Za-z0-9_.-]*")
        return value

    def boolean(self, obj: Any, path: str) -> bool:
        if type(obj) is not bool:
            raise ConfigurationError(f"{path}: expected boolean")
        return obj

    def integer(self, obj: Any, path: str, *, minimum: int = 0) -> int:
        if type(obj) is not int or obj < minimum:
            raise ConfigurationError(f"{path}: expected integer >= {minimum}")
        return obj

    def sequence(self, obj: Any, path: str) -> list[Any]:
        if not isinstance(obj, list):
            raise ConfigurationError(f"{path}: expected array")
        return obj

    def timestamp(self, obj: Any, path: str) -> str:
        value = self.string(obj, path)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ConfigurationError(f"{path}: invalid ISO-8601 UTC timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ConfigurationError(f"{path}: timestamp must explicitly be UTC")
        return value

    def param(
        self,
        obj: Any,
        path: str,
        unit: str,
        *,
        default: Any = _MISSING,
        minimum: float | None = None,
        maximum: float | None = None,
        strict_minimum: bool = False,
        strict_maximum: bool = False,
    ) -> Parameter:
        is_default = obj is _MISSING
        if is_default:
            if default is _MISSING:
                raise ConfigurationError(f"{path}: required parameter missing")
            self.default(path)
            obj = {"value": default, "unit": unit, "is_default": True}
        obj = self.mapping(
            obj,
            path,
            {"value", "unit", "certainty", "note", "source", "lower_bound", "upper_bound", "is_default"},
        )
        value = self.required(obj, "value", path)
        given_unit = self.required(obj, "unit", path)
        if given_unit != unit or type(given_unit) is not str:
            raise ConfigurationError(f"{path}.unit: expected canonical unit {unit!r}")

        def finite_number(number: Any, field: str) -> int | float:
            if type(number) not in (int, float):
                raise ConfigurationError(f"{path}.{field}: expected finite number (not boolean)")
            try:
                is_finite = math.isfinite(float(number))
            except OverflowError:
                is_finite = False
            if not is_finite:
                raise ConfigurationError(f"{path}.{field}: expected finite number (not boolean)")
            return number

        nominal = finite_number(value, "value")
        certainty = self.string(obj.get("certainty", "guesstimate"), f"{path}.certainty")
        if certainty not in CERTAINTIES:
            raise ConfigurationError(f"{path}.certainty: invalid certainty {certainty!r}")
        note = obj.get("note")
        source = obj.get("source")
        for key, item in (("note", note), ("source", source)):
            if item is not None and not isinstance(item, str):
                raise ConfigurationError(f"{path}.{key}: expected string or null")
        lower = obj.get("lower_bound")
        upper = obj.get("upper_bound")
        if lower is not None:
            lower = finite_number(lower, "lower_bound")
        if upper is not None:
            upper = finite_number(upper, "upper_bound")
        if lower is not None and lower > nominal:
            raise ConfigurationError(f"{path}: lower_bound exceeds value")
        if upper is not None and upper < nominal:
            raise ConfigurationError(f"{path}: upper_bound is below value")
        if minimum is not None and (nominal <= minimum if strict_minimum else nominal < minimum):
            op = ">" if strict_minimum else ">="
            raise ConfigurationError(f"{path}.value: must be {op} {minimum}")
        if maximum is not None and (nominal >= maximum if strict_maximum else nominal > maximum):
            op = "<" if strict_maximum else "<="
            raise ConfigurationError(f"{path}.value: must be {op} {maximum}")
        explicit_default = self.boolean(obj.get("is_default", False), f"{path}.is_default")
        return Parameter(
            nominal, unit, certainty, note, source, lower, upper,
            is_default=is_default or explicit_default,
        )


def _unique(items: list[Any], path: str) -> None:
    seen: set[str] = set()
    for i, item in enumerate(items):
        if item.id in seen:
            raise ConfigurationError(f"{path}[{i}].id: duplicate ID {item.id!r}")
        seen.add(item.id)


def _reference(id_value: str, ids: set[str], path: str) -> None:
    if id_value not in ids:
        raise ConfigurationError(f"{path}: unknown reference {id_value!r}")


def _orbit(reader: _Reader, raw: Any, simulation: SimulationConfig) -> OrbitalElements:
    path = "orbit"
    obj = reader.mapping(
        raw, path,
        {"circular_altitude_m", "semi_major_axis_m", "eccentricity", "inclination_deg",
         "raan_deg", "argument_of_periapsis_deg", "mean_anomaly_at_epoch_deg",
         "epoch_utc", "frame", "propagator"},
    )
    circular = "circular_altitude_m" in obj
    advanced = "semi_major_axis_m" in obj
    if circular == advanced:
        raise ConfigurationError(
            "orbit: provide exactly one of circular_altitude_m or semi_major_axis_m"
        )
    if circular:
        if "eccentricity" in obj:
            raise ConfigurationError("orbit.eccentricity: circular form fixes eccentricity to zero")
        alt = reader.param(obj["circular_altitude_m"], "orbit.circular_altitude_m", "m", minimum=0)
        sma = Parameter(
            value=alt.value + EARTH_EQUATORIAL_RADIUS_M,
            unit="m",
            certainty="calculated_estimate",
            note="Circular convenience form: altitude + WGS-84 equatorial radius (6378137 m)",
            source=alt.source,
            lower_bound=(alt.lower_bound + EARTH_EQUATORIAL_RADIUS_M if alt.lower_bound is not None else None),
            upper_bound=(alt.upper_bound + EARTH_EQUATORIAL_RADIUS_M if alt.upper_bound is not None else None),
        )
        eccentricity = reader.param(_MISSING, "orbit.eccentricity", "1", default=0)
    else:
        sma = reader.param(obj["semi_major_axis_m"], "orbit.semi_major_axis_m", "m",
                           minimum=EARTH_EQUATORIAL_RADIUS_M, strict_minimum=True)
        eccentricity = reader.param(reader.required(obj, "eccentricity", path),
                                    "orbit.eccentricity", "1", minimum=0, maximum=1,
                                    strict_maximum=True)
    inc = reader.param(reader.required(obj, "inclination_deg", path),
                       "orbit.inclination_deg", "deg", minimum=0, maximum=180)
    raan = reader.param(obj.get("raan_deg", _MISSING), "orbit.raan_deg", "deg",
                        default=0, minimum=0, maximum=360)
    arg = reader.param(obj.get("argument_of_periapsis_deg", _MISSING),
                       "orbit.argument_of_periapsis_deg", "deg", default=0,
                       minimum=0, maximum=360)
    mean = reader.param(obj.get("mean_anomaly_at_epoch_deg", _MISSING),
                        "orbit.mean_anomaly_at_epoch_deg", "deg", default=0,
                        minimum=0, maximum=360)
    if sma.value * (1 - eccentricity.value) <= EARTH_EQUATORIAL_RADIUS_M:
        raise ConfigurationError("orbit: perigee is inside Earth")
    epoch = reader.timestamp(reader.optional(obj, "epoch_utc", simulation.epoch_utc, path),
                             "orbit.epoch_utc")
    frame = reader.string(reader.optional(obj, "frame", "ECI_J2000", path), "orbit.frame")
    if frame != "ECI_J2000":
        raise ConfigurationError("orbit.frame: only ECI_J2000 is supported")
    propagator = reader.string(reader.optional(obj, "propagator", "kepler", path),
                               "orbit.propagator")
    if propagator not in {"kepler", "kepler_j2"}:
        raise ConfigurationError("orbit.propagator: expected 'kepler' or 'kepler_j2'")
    return OrbitalElements(sma, eccentricity, inc, raan, arg, mean, epoch, frame, propagator)


def _defaults(reader: _Reader, raw: Any, mode_ids: set[str], queue_ids: set[str]) -> Defaults:
    path = "defaults"
    obj = reader.mapping(raw, path, {
        "initial_mode_id", "default_producer_queue_id", "default_processor_input_queue_id",
        "default_processor_output_queue_id", "default_downlink_queue_id",
        "default_uplink_queue_id", "retain_raw_after_processing",
    })
    first = reader.ident(reader.required(obj, "initial_mode_id", path),
                         "defaults.initial_mode_id")
    _reference(first, mode_ids, "defaults.initial_mode_id")
    queue_fields = {
        "default_producer_queue_id": "raw",
        "default_processor_input_queue_id": "raw",
        "default_processor_output_queue_id": "processed",
        "default_downlink_queue_id": "processed",
        "default_uplink_queue_id": "raw",
    }
    routes: dict[str, str] = {}
    for key, fallback in queue_fields.items():
        routes[key] = reader.ident(reader.optional(obj, key, fallback, path), f"{path}.{key}")
        _reference(routes[key], queue_ids, f"{path}.{key}")
    retain = reader.boolean(reader.optional(obj, "retain_raw_after_processing", False, path),
                            "defaults.retain_raw_after_processing")
    return Defaults(first, *(routes[k] for k in queue_fields), retain)


def _component(
    reader: _Reader, raw: Any, index: int, mode_ids: set[str], defaults: Defaults,
) -> Component:
    path = f"components[{index}]"
    obj = reader.mapping(raw, path, {"id", "name", "mass_kg", "capabilities", "mode_values"})
    ident = reader.ident(reader.required(obj, "id", path), f"{path}.id")
    name = reader.string(reader.required(obj, "name", path), f"{path}.name")
    mass = reader.param(reader.required(obj, "mass_kg", path), f"{path}.mass_kg", "kg", minimum=0)
    caps = reader.mapping(reader.required(obj, "capabilities", path), f"{path}.capabilities",
                          {"load", "generator", "battery", "producer", "processor", "storage", "radio"})
    if not caps:
        raise ConfigurationError(f"{path}.capabilities: at least one capability required")
    parsed: dict[str, Any] = {}
    cp = f"{path}.capabilities"
    if "load" in caps:
        p = f"{cp}.load"
        c = reader.mapping(caps["load"], p, {"essential", "shedding_priority", "enabled"})
        parsed["load"] = LoadCapability(
            reader.boolean(reader.optional(c, "essential", False, p), f"{p}.essential"),
            reader.integer(reader.optional(c, "shedding_priority", 100, p), f"{p}.shedding_priority"),
            reader.boolean(reader.optional(c, "enabled", True, p), f"{p}.enabled"),
        )
    if "generator" in caps:
        p = f"{cp}.generator"
        c = reader.mapping(caps["generator"], p, {"sunlight_dependent"})
        parsed["generator"] = GeneratorCapability(
            reader.boolean(reader.optional(c, "sunlight_dependent", True, p),
                           f"{p}.sunlight_dependent")
        )
    if "battery" in caps:
        p = f"{cp}.battery"
        c = reader.mapping(caps["battery"], p, {
            "capacity_wh", "initial_energy_wh", "charge_efficiency", "discharge_efficiency",
            "max_charge_w", "max_discharge_w",
        })
        field_specs = {
            "capacity_wh": ("Wh", 0, None, True),
            "initial_energy_wh": ("Wh", 0, None, False),
            "charge_efficiency": ("1", 0, 1, True),
            "discharge_efficiency": ("1", 0, 1, True),
            "max_charge_w": ("W", 0, None, False),
            "max_discharge_w": ("W", 0, None, False),
        }
        vals = {}
        for key, (unit, low, high, exclusive) in field_specs.items():
            vals[key] = reader.param(reader.required(c, key, p), f"{p}.{key}", unit,
                                     minimum=low, maximum=high, strict_minimum=exclusive)
        if vals["initial_energy_wh"].value > vals["capacity_wh"].value:
            raise ConfigurationError(f"{p}.initial_energy_wh: exceeds capacity_wh")
        parsed["battery"] = BatteryCapability(**vals)
    if "producer" in caps:
        p = f"{cp}.producer"
        c = reader.mapping(caps["producer"], p, {"destination_queue_id"})
        parsed["producer"] = ProducerCapability(reader.ident(
            reader.optional(c, "destination_queue_id", defaults.default_producer_queue_id, p),
            f"{p}.destination_queue_id",
        ))
    if "processor" in caps:
        p = f"{cp}.processor"
        c = reader.mapping(caps["processor"], p, {
            "source_queue_id", "destination_queue_id", "output_input_ratio", "retain_raw",
        })
        parsed["processor"] = ProcessorCapability(
            reader.ident(reader.optional(c, "source_queue_id", defaults.default_processor_input_queue_id, p),
                         f"{p}.source_queue_id"),
            reader.ident(reader.optional(c, "destination_queue_id", defaults.default_processor_output_queue_id, p),
                         f"{p}.destination_queue_id"),
            reader.param(reader.required(c, "output_input_ratio", p),
                         f"{p}.output_input_ratio", "1", minimum=0),
            reader.boolean(reader.optional(c, "retain_raw", defaults.retain_raw_after_processing, p),
                           f"{p}.retain_raw"),
        )
    if "storage" in caps:
        p = f"{cp}.storage"
        c = reader.mapping(caps["storage"], p, {"usable_bytes", "initial_queue_bytes"})
        capacity = reader.param(reader.required(c, "usable_bytes", p),
                                f"{p}.usable_bytes", "byte", minimum=0)
        initials = reader.mapping(reader.optional(c, "initial_queue_bytes", {}, p),
                                  f"{p}.initial_queue_bytes", set(defaults_queue_ids(reader)))
        # The allowed-keys check for queue IDs is intentionally deferred until
        # the complete project's queue set is available.
        parsed["storage"] = StorageCapability(capacity, {
            q: reader.param(v, f"{p}.initial_queue_bytes.{q}", "byte", minimum=0)
            for q, v in initials.items()
        })
        if sum(v.value for v in parsed["storage"].initial_queue_bytes.values()) > capacity.value:
            raise ConfigurationError(f"{p}.initial_queue_bytes: exceeds usable_bytes")
    if "radio" in caps:
        p = f"{cp}.radio"
        c = reader.mapping(caps["radio"], p, {
            "supported_station_ids", "downlink_queue_id", "uplink_queue_id",
        })
        station_ids = tuple(reader.ident(v, f"{p}.supported_station_ids[{i}]") for i, v in
                            enumerate(reader.sequence(reader.required(c, "supported_station_ids", p),
                                                      f"{p}.supported_station_ids")))
        if len(set(station_ids)) != len(station_ids):
            raise ConfigurationError(f"{p}.supported_station_ids: duplicate station ID")
        down = reader.ident(reader.optional(c, "downlink_queue_id", defaults.default_downlink_queue_id, p),
                            f"{p}.downlink_queue_id")
        up = c.get("uplink_queue_id")
        if up is not None:
            up = reader.ident(up, f"{p}.uplink_queue_id")
        parsed["radio"] = RadioCapability(station_ids, down, up)
    mv_path = f"{path}.mode_values"
    modes = reader.mapping(reader.optional(obj, "mode_values", {}, path), mv_path, mode_ids)
    specs: dict[str, tuple[str | None, str, int]] = {
        "active": ("load", "bool", 0),
        "idle_power_w": ("load", "W", 0),
        "active_power_w": ("load", "W", 0),
        "idle_current_a": ("load", "A", 0),
        "active_current_a": ("load", "A", 0),
        "generation_w": ("generator", "W", 0),
        "data_generation_bytes_per_s": ("producer", "byte/s", 0),
        "processing_input_bytes_per_s": ("processor", "byte/s", 0),
        "downlink_bps": ("radio", "bit/s", 0),
        "uplink_bps": ("radio", "bit/s", 0),
    }
    mode_values = {}
    for mid in sorted(mode_ids):
        mp = f"{mv_path}.{mid}"
        if mid not in modes:
            reader.default(mp)
        values = reader.mapping(modes.get(mid, {}), mp, set(specs))
        fields: dict[str, Any] = {}
        for key, (capability, unit, default) in specs.items():
            if capability not in parsed:
                if key in values:
                    raise ConfigurationError(f"{mp}.{key}: requires {capability} capability")
                continue
            v = values.get(key, _MISSING)
            if unit == "bool":
                if v is _MISSING:
                    reader.default(f"{mp}.{key}")
                    v = False
                fields[key] = reader.boolean(v, f"{mp}.{key}")
            else:
                fields[key] = reader.param(v, f"{mp}.{key}", unit, default=default, minimum=0)
        mode_values[mid] = ModeValues(**fields)
    return Component(ident, name, mass, mode_values, **parsed)


def defaults_queue_ids(reader: _Reader) -> set[str]:
    """Return IDs of the currently validated project queues."""
    return reader.queue_ids


def _station(reader: _Reader, raw: Any, i: int) -> GroundStation:
    path = f"ground_stations[{i}]"
    obj = reader.mapping(raw, path, {
        "id", "name", "latitude_deg", "longitude_deg", "altitude_m", "minimum_elevation_deg",
        "effective_downlink_bps", "effective_uplink_bps", "supported_radio_ids", "availability",
    })
    ident = reader.ident(reader.required(obj, "id", path), f"{path}.id")
    name = reader.string(reader.required(obj, "name", path), f"{path}.name")
    latitude = reader.param(reader.required(obj, "latitude_deg", path),
                            f"{path}.latitude_deg", "deg", minimum=-90, maximum=90)
    longitude = reader.param(reader.required(obj, "longitude_deg", path),
                             f"{path}.longitude_deg", "deg", minimum=-180, maximum=180)
    altitude = reader.param(reader.required(obj, "altitude_m", path), f"{path}.altitude_m", "m")
    minimum = reader.param(reader.required(obj, "minimum_elevation_deg", path),
                           f"{path}.minimum_elevation_deg", "deg", minimum=0, maximum=90)
    downlink = reader.param(reader.required(obj, "effective_downlink_bps", path),
                            f"{path}.effective_downlink_bps", "bit/s", minimum=0)
    uplink = reader.param(obj.get("effective_uplink_bps", _MISSING),
                          f"{path}.effective_uplink_bps", "bit/s", default=0, minimum=0)
    radios = tuple(reader.ident(v, f"{path}.supported_radio_ids[{j}]") for j, v in enumerate(
        reader.sequence(reader.required(obj, "supported_radio_ids", path),
                        f"{path}.supported_radio_ids")))
    if len(set(radios)) != len(radios):
        raise ConfigurationError(f"{path}.supported_radio_ids: duplicate radio ID")
    intervals = []
    for j, entry in enumerate(reader.sequence(reader.optional(obj, "availability", [], path),
                                              f"{path}.availability")):
        p = f"{path}.availability[{j}]"
        entry = reader.mapping(entry, p, {"start_utc", "end_utc"})
        start = reader.timestamp(reader.required(entry, "start_utc", p), f"{p}.start_utc")
        end = reader.timestamp(reader.required(entry, "end_utc", p), f"{p}.end_utc")
        if _utc(end) <= _utc(start):
            raise ConfigurationError(f"{p}: end_utc must be after start_utc")
        intervals.append(AvailabilityInterval(start, end))
    _check_overlap([(_utc(v.start_utc), _utc(v.end_utc)) for v in intervals],
                   f"{path}.availability")
    return GroundStation(ident, name, latitude, longitude, altitude, minimum,
                         downlink, uplink, radios, tuple(intervals))


def _utc(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _check_overlap(ranges: list[tuple[Any, Any]], path: str) -> None:
    ordered = sorted(ranges)
    for i in range(1, len(ordered)):
        if ordered[i][0] < ordered[i - 1][1]:
            raise ConfigurationError(f"{path}: intervals overlap")


def _actions(reader: _Reader, raw: Any, path: str, modes: set[str], queues: set[str]) -> Actions:
    obj = reader.mapping(raw, path, {
        "mode_id", "pointing", "processing_enabled", "downlink_enabled",
        "reset_overrides", "delete_requests",
    })
    mid = obj.get("mode_id")
    if mid is not None:
        mid = reader.ident(mid, f"{path}.mode_id")
        _reference(mid, modes, f"{path}.mode_id")
    pointing = obj.get("pointing")
    if pointing is not None:
        pointing = reader.string(pointing, f"{path}.pointing")
        if pointing not in POINTINGS:
            raise ConfigurationError(f"{path}.pointing: unsupported pointing {pointing!r}")
    processing = obj.get("processing_enabled")
    downlink = obj.get("downlink_enabled")
    if processing is not None:
        processing = reader.boolean(processing, f"{path}.processing_enabled")
    if downlink is not None:
        downlink = reader.boolean(downlink, f"{path}.downlink_enabled")
    reset = reader.boolean(reader.optional(obj, "reset_overrides", False, path),
                           f"{path}.reset_overrides")
    deletes = []
    for i, entry in enumerate(reader.sequence(reader.optional(obj, "delete_requests", [], path),
                                              f"{path}.delete_requests")):
        p = f"{path}.delete_requests[{i}]"
        item = reader.mapping(entry, p, {"queue_id", "bytes"})
        queue = reader.ident(reader.required(item, "queue_id", p), f"{p}.queue_id")
        _reference(queue, queues, f"{p}.queue_id")
        amount = reader.param(reader.required(item, "bytes", p), f"{p}.bytes", "byte", minimum=0)
        deletes.append(DeleteRequest(queue, amount))
    return Actions(mid, pointing, processing, downlink, reset, tuple(deletes))


_STATUS_FIELDS: dict[str, str] = {
    "elapsed_seconds": "s", "seconds_in_mode": "s",
    "battery_energy_wh": "Wh", "battery_percent": "%",
    "storage_used_bytes": "byte", "storage_capacity_bytes": "byte",
    "downlink_queue_bytes": "byte", "queue_bytes": "byte",
    "latitude_deg": "deg", "longitude_deg": "deg", "altitude_m": "m",
    "available_downlink_bps": "bit/s", "previous_generation_w": "W",
    "previous_consumption_w": "W", "previous_unmet_load_w": "W",
    "mode_id": "str", "in_eclipse": "bool", "ground_station_visible": "bool",
}


def _condition(
    reader: _Reader, raw: Any, path: str, modes: set[str], queues: set[str], depth: int = 0,
) -> Condition:
    if depth >= 16:
        raise ConfigurationError(f"{path}: condition nesting exceeds 16")
    obj = reader.mapping(raw, path, {"all", "any", "not", "field", "op", "value", "queue_id"})
    kinds = [k for k in ("all", "any", "not") if k in obj]
    if kinds:
        if len(kinds) != 1 or len(obj) != 1:
            raise ConfigurationError(f"{path}: logical condition must have one operator")
        kind = kinds[0]
        if kind == "not":
            return Condition(kind, children=(_condition(reader, obj[kind], f"{path}.not",
                                                        modes, queues, depth + 1),))
        children = reader.sequence(obj[kind], f"{path}.{kind}")
        if not children:
            raise ConfigurationError(f"{path}.{kind}: cannot be empty")
        return Condition(kind, children=tuple(
            _condition(reader, item, f"{path}.{kind}[{i}]", modes, queues, depth + 1)
            for i, item in enumerate(children)
        ))
    field = reader.string(reader.required(obj, "field", path), f"{path}.field")
    if field not in _STATUS_FIELDS:
        raise ConfigurationError(f"{path}.field: unsupported status field {field!r}")
    op = reader.string(reader.required(obj, "op", path), f"{path}.op")
    if op not in {"<", "<=", "==", "!=", ">=", ">"}:
        raise ConfigurationError(f"{path}.op: invalid comparison")
    queue = obj.get("queue_id")
    if field == "queue_bytes":
        queue = reader.ident(queue, f"{path}.queue_id")
        _reference(queue, queues, f"{path}.queue_id")
    elif queue is not None:
        raise ConfigurationError(f"{path}.queue_id: only valid for queue_bytes")
    dtype = _STATUS_FIELDS[field]
    value = reader.required(obj, "value", path)
    if dtype == "bool":
        if op not in {"==", "!="}:
            raise ConfigurationError(f"{path}.op: boolean comparison must use == or !=")
        value = reader.boolean(value, f"{path}.value")
    elif dtype == "str":
        if op not in {"==", "!="}:
            raise ConfigurationError(f"{path}.op: ID comparison must use == or !=")
        value = reader.ident(value, f"{path}.value")
        _reference(value, modes, f"{path}.value")
    else:
        value = reader.param(value, f"{path}.value", dtype)
    return Condition("comparison", field, op, value, queue)


def _control(reader: _Reader, raw: Any, modes: set[str], queues: set[str]) -> ControlConfig:
    path = "control"
    obj = reader.mapping(raw, path, {
        "type", "script_path", "script_source", "intervals", "rules", "fallback",
    })
    kind = reader.string(reader.optional(obj, "type", "none", path), f"{path}.type")
    if kind not in {"none", "python", "schedule", "blocks"}:
        raise ConfigurationError(f"{path}.type: unsupported controller type {kind!r}")
    allowed_by_kind = {
        "none": {"type"},
        "python": {"type", "script_path", "script_source"},
        "schedule": {"type", "intervals", "fallback"},
        "blocks": {"type", "rules", "fallback"},
    }
    extras = set(obj) - allowed_by_kind[kind]
    if extras:
        raise ConfigurationError(f"{path}: fields not valid for {kind}: {', '.join(sorted(extras))}")
    if kind == "none":
        return ControlConfig()
    if kind == "python":
        script = obj.get("script_path")
        source = obj.get("script_source")
        if (script is None) == (source is None):
            raise ConfigurationError("control: provide exactly one of script_path or script_source")
        if script is not None:
            script = reader.string(script, "control.script_path")
        if source is not None:
            source = reader.string(source, "control.script_source")
        return ControlConfig(kind, script, source)
    fallback = _actions(reader, reader.required(obj, "fallback", path),
                        f"{path}.fallback", modes, queues)
    if kind == "schedule":
        intervals = []
        bases: set[str] = set()
        ranges: list[tuple[Any, Any]] = []
        for i, raw_interval in enumerate(reader.sequence(reader.required(obj, "intervals", path),
                                                         "control.intervals")):
            p = f"control.intervals[{i}]"
            v = reader.mapping(raw_interval, p, {
                "start_elapsed_s", "end_elapsed_s", "start_utc", "end_utc", "actions",
            })
            has_elapsed = "start_elapsed_s" in v or "end_elapsed_s" in v
            has_utc = "start_utc" in v or "end_utc" in v
            if has_elapsed == has_utc:
                raise ConfigurationError(f"{p}: provide either elapsed or UTC interval bounds")
            actions = _actions(reader, reader.required(v, "actions", p), f"{p}.actions",
                               modes, queues)
            if has_elapsed:
                start = reader.param(reader.required(v, "start_elapsed_s", p),
                                     f"{p}.start_elapsed_s", "s", minimum=0)
                end = reader.param(reader.required(v, "end_elapsed_s", p),
                                   f"{p}.end_elapsed_s", "s", minimum=0)
                if end.value <= start.value:
                    raise ConfigurationError(f"{p}: end must follow start")
                bases.add("elapsed")
                ranges.append((start.value, end.value))
                intervals.append(ScheduleInterval(actions, start, end))
            else:
                start = reader.timestamp(reader.required(v, "start_utc", p), f"{p}.start_utc")
                end = reader.timestamp(reader.required(v, "end_utc", p), f"{p}.end_utc")
                if _utc(end) <= _utc(start):
                    raise ConfigurationError(f"{p}: end must follow start")
                bases.add("utc")
                ranges.append((_utc(start), _utc(end)))
                intervals.append(ScheduleInterval(actions, start_utc=start, end_utc=end))
        if len(bases) > 1:
            raise ConfigurationError("control.intervals: cannot mix UTC and elapsed intervals")
        _check_overlap(ranges, "control.intervals")
        return ControlConfig(kind, intervals=tuple(intervals), fallback=fallback)
    rules = []
    for i, raw_rule in enumerate(reader.sequence(reader.required(obj, "rules", path),
                                                 "control.rules")):
        p = f"control.rules[{i}]"
        rule = reader.mapping(raw_rule, p, {"condition", "actions"})
        rules.append(BlockRule(
            _condition(reader, reader.required(rule, "condition", p),
                       f"{p}.condition", modes, queues),
            _actions(reader, reader.required(rule, "actions", p), f"{p}.actions",
                     modes, queues),
        ))
    return ControlConfig(kind, rules=tuple(rules), fallback=fallback)


def validate_configuration(raw: dict[str, Any]) -> ResolvedConfiguration:
    """Validate a JSON-ready project and return typed, resolved configuration.

    Raises ``ConfigurationError`` with a field path on invalid input.  This
    function never changes ``raw``.  Unknown fields are rejected to prevent
    their being silently discarded during future editing or serialization.
    """
    reader = _Reader()
    obj = reader.mapping(raw, "$", {
        "schema_version", "project", "simulation", "orbit", "modes", "components",
        "ground_stations", "data_queues", "control", "defaults",
    })
    version = reader.string(reader.required(obj, "schema_version", "$"), "schema_version")
    if version != SCHEMA_VERSION:
        raise ConfigurationError(f"schema_version: expected {SCHEMA_VERSION!r}")
    p = reader.mapping(reader.required(obj, "project", "$"), "project",
                       {"id", "title", "description"})
    project = ProjectInfo(
        reader.ident(reader.required(p, "id", "project"), "project.id"),
        reader.string(reader.required(p, "title", "project"), "project.title"),
        reader.string(reader.optional(p, "description", "", "project"),
                      "project.description", nonempty=False),
    )
    p = reader.mapping(reader.required(obj, "simulation", "$"), "simulation", {
        "epoch_utc", "duration_s", "calculation_step_s", "output_interval_s",
    })
    epoch = reader.timestamp(reader.required(p, "epoch_utc", "simulation"),
                             "simulation.epoch_utc")
    duration = reader.param(reader.required(p, "duration_s", "simulation"),
                            "simulation.duration_s", "s", minimum=0, strict_minimum=True)
    step = reader.param(p.get("calculation_step_s", _MISSING), "simulation.calculation_step_s",
                        "s", default=20, minimum=0, strict_minimum=True)
    output = reader.param(p.get("output_interval_s", _MISSING), "simulation.output_interval_s",
                          "s", default=max(60, step.value), minimum=0, strict_minimum=True)
    if output.value < step.value:
        raise ConfigurationError("simulation.output_interval_s: cannot be less than calculation_step_s")
    simulation = SimulationConfig(epoch, duration, step, output)
    orbit = _orbit(reader, reader.required(obj, "orbit", "$"), simulation)
    modes = []
    for i, raw_mode in enumerate(reader.sequence(reader.required(obj, "modes", "$"), "modes")):
        path = f"modes[{i}]"
        m = reader.mapping(raw_mode, path, {"id", "label", "default_pointing"})
        mode = Mode(
            reader.ident(reader.required(m, "id", path), f"{path}.id"),
            reader.string(reader.required(m, "label", path), f"{path}.label"),
            reader.string(reader.optional(m, "default_pointing", "sun", path),
                          f"{path}.default_pointing"),
        )
        if mode.default_pointing not in POINTINGS:
            raise ConfigurationError(f"{path}.default_pointing: invalid pointing")
        modes.append(mode)
    if not modes:
        raise ConfigurationError("modes: at least one mode required")
    _unique(modes, "modes")
    mode_ids = {m.id for m in modes}
    raw_queues = reader.optional(obj, "data_queues", [
        {"id": "raw", "label": "Raw"}, {"id": "processed", "label": "Processed"},
    ], "$")
    queues = []
    for i, raw_queue in enumerate(reader.sequence(raw_queues, "data_queues")):
        path = f"data_queues[{i}]"
        q = reader.mapping(raw_queue, path, {"id", "label"})
        ident = reader.ident(reader.required(q, "id", path), f"{path}.id")
        queues.append(DataQueue(ident, reader.string(reader.optional(q, "label", ident, path),
                                               f"{path}.label")))
    if not queues:
        raise ConfigurationError("data_queues: at least one queue required")
    _unique(queues, "data_queues")
    queue_ids = {q.id for q in queues}
    reader.queue_ids = queue_ids
    defaults = _defaults(reader, reader.required(obj, "defaults", "$"), mode_ids, queue_ids)
    components = [
        _component(reader, item, i, mode_ids, defaults)
        for i, item in enumerate(reader.sequence(reader.required(obj, "components", "$"), "components"))
    ]
    _unique(components, "components")
    for key in ("battery", "storage"):
        if sum(getattr(c, key) is not None for c in components) > 1:
            raise ConfigurationError(f"components: at most one {key} capability is supported")
    stations = [
        _station(reader, item, i)
        for i, item in enumerate(reader.sequence(reader.optional(obj, "ground_stations", [], "$"),
                                                 "ground_stations"))
    ]
    _unique(stations, "ground_stations")
    station_ids = {s.id for s in stations}
    radio_ids = {c.id for c in components if c.radio is not None}
    for c in components:
        base = f"components[{c.id}].capabilities"
        if c.producer:
            _reference(c.producer.destination_queue_id, queue_ids, f"{base}.producer.destination_queue_id")
        if c.processor:
            _reference(c.processor.source_queue_id, queue_ids, f"{base}.processor.source_queue_id")
            _reference(c.processor.destination_queue_id, queue_ids, f"{base}.processor.destination_queue_id")
            if c.processor.source_queue_id == c.processor.destination_queue_id:
                raise ConfigurationError(f"{base}.processor: source and destination queues must differ")
        if c.storage:
            for q in c.storage.initial_queue_bytes:
                _reference(q, queue_ids, f"{base}.storage.initial_queue_bytes.{q}")
        if c.radio:
            for station in c.radio.supported_station_ids:
                _reference(station, station_ids, f"{base}.radio.supported_station_ids")
            _reference(c.radio.downlink_queue_id, queue_ids, f"{base}.radio.downlink_queue_id")
            if c.radio.uplink_queue_id is not None:
                _reference(c.radio.uplink_queue_id, queue_ids, f"{base}.radio.uplink_queue_id")
    for s in stations:
        for radio in s.supported_radio_ids:
            _reference(radio, radio_ids, f"ground_stations[{s.id}].supported_radio_ids")
    control = _control(reader, reader.optional(obj, "control", {"type": "none"}, "$"),
                       mode_ids, queue_ids)
    return ResolvedConfiguration(
        version, project, simulation, orbit, tuple(modes), tuple(components),
        tuple(stations), tuple(queues), control, defaults,
        tuple(reader.defaults_applied), copy.deepcopy(raw),
    )


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ConfigurationError(f"JSON: duplicate object key {key!r}")
        obj[key] = value
    return obj


def _bad_constant(value: str) -> None:
    raise ConfigurationError(f"JSON: nonfinite number {value!r} is not permitted")


def load_configuration(path: str | Path) -> ResolvedConfiguration:
    """Read JSON, reject duplicate keys, and return validated resolved input."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"),
                         object_pairs_hook=_no_duplicates, parse_constant=_bad_constant)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ConfigurationError(f"{path}: invalid JSON: {exc}") from exc
    return validate_configuration(raw)


def resolved_to_dict(configuration: ResolvedConfiguration) -> dict[str, Any]:
    """Return a JSON-friendly typed snapshot, with defaults and provenance."""
    result = asdict(configuration)
    result.pop("original")
    return result


def save_configuration(
    configuration: ResolvedConfiguration | dict[str, Any],
    path: str | Path,
    *,
    resolved: bool = False,
) -> None:
    """Save the unmodified original by default, or an annotated resolved snapshot.

    A resolved snapshot is intended for run records, inspection and reports;
    its extra ``defaults_applied`` and derived elements are not the project
    input schema.  Only ``resolved=False`` creates a reloadable project file.
    """
    if isinstance(configuration, dict):
        configuration = validate_configuration(configuration)
    raw = resolved_to_dict(configuration) if resolved else configuration.original
    # Always validate the project representation before writing.
    if not resolved:
        validate_configuration(raw)
    content = json.dumps(raw, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    Path(path).write_text(content, encoding="utf-8")
