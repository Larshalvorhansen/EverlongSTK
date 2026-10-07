"""Shared EverlongSTK data containers.

Per specV2.md §4 (Project configuration), §5 (Orbit and environment),
§6.1 (Python policy contract), and §9 (Data accounting).
Units follow CONTRACT.md §1. This module contains data containers only:
no I/O, physics, validation, or simulation logic.
"""

from dataclasses import dataclass
from typing import Any, Literal, Optional


Certainty = Literal[
    "guesstimate",
    "calculated_estimate",
    "specified",
    "tested",
]


@dataclass
class ParameterValue:
    value: float
    unit: str
    certainty: Certainty
    is_default: bool
    note: Optional[str]
    source: Optional[str]
    lower_bound: Optional[float]
    upper_bound: Optional[float]


@dataclass
class Project:
    id: str
    title: str
    description: str


@dataclass
class Simulation:
    utc_epoch: str
    duration_s: float
    calculation_step_s: float
    output_interval_s: float


@dataclass
class Orbit:
    propagator: str
    frame: str
    semi_major_axis_m: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    arg_periapsis_deg: float
    mean_anomaly_deg: float
    utc_epoch: str


@dataclass
class Mode:
    id: str
    label: str
    default_pointing: str


@dataclass
class Component:
    id: str
    name: str
    mass_kg: ParameterValue
    capabilities: list[str]
    hardware_limits: dict[str, Any]
    # Expected inner keys include "active", "idle_power_w", "active_power_w",
    # "generation_w", "data_rate_bytes_s", etc.; shape is not enforced in Phase 1.
    mode_values: dict[str, dict[str, Any]]


@dataclass
class GroundStation:
    id: str
    lat_deg: ParameterValue
    lon_deg: ParameterValue
    alt_m: ParameterValue
    min_elevation_deg: ParameterValue
    availability: list[Any]
    supported_radio_ids: list[str]
    uplink_bps: ParameterValue
    downlink_bps: ParameterValue


@dataclass
class DataQueue:
    id: str
    label: str
    initial_bytes: ParameterValue


@dataclass
class Control:
    type: Literal["schedule", "blocks", "python"]
    payload: Any


@dataclass
class Defaults:
    initial_mode_id: str
    resource_behavior: Any
    queue_routing: Any


@dataclass(frozen=True)
class DeleteRequest:
    queue_id: str
    bytes: int


@dataclass(frozen=True)
class Actions:
    mode_id: Optional[str] = None
    pointing: Optional[str] = None
    processing_enabled: Optional[bool] = None
    downlink_enabled: Optional[bool] = None
    delete_requests: Optional[tuple[DeleteRequest, ...]] = None


@dataclass(frozen=True)
class Status:
    time_utc: str
    elapsed_seconds: float
    mode_id: str
    seconds_in_mode: float
    battery_energy_wh: float
    battery_percent: float
    storage_used_bytes: int
    storage_capacity_bytes: int
    queue_bytes: dict[str, int]
    downlink_queue_bytes: int
    position_eci_m: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    in_eclipse: bool
    visible_ground_stations: tuple[str, ...]
    ground_station_visible: bool
    available_downlink_bps: float
    previous_generation_w: float
    previous_consumption_w: float
    previous_unmet_load_w: float


__all__ = [
    "ParameterValue",
    "Project",
    "Simulation",
    "Orbit",
    "Mode",
    "Component",
    "GroundStation",
    "DataQueue",
    "Control",
    "Defaults",
    "DeleteRequest",
    "Actions",
    "Status",
]
