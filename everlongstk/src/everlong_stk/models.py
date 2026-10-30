"""Shared, unit-explicit configuration and control data types.

These objects intentionally contain no simulation, I/O, or GUI behavior.  A
configuration is constructed by ``configuration.validate_configuration``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class Parameter:
    """A numerical engineering input and its provenance (canonical unit)."""

    value: int | float
    unit: str
    certainty: str = "guesstimate"
    note: str | None = None
    source: str | None = None
    lower_bound: int | float | None = None
    upper_bound: int | float | None = None
    is_default: bool = False


@dataclass(frozen=True)
class ProjectInfo:
    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class SimulationConfig:
    epoch_utc: str
    duration_s: Parameter
    calculation_step_s: Parameter
    output_interval_s: Parameter


@dataclass(frozen=True)
class OrbitalElements:
    semi_major_axis_m: Parameter
    eccentricity: Parameter
    inclination_deg: Parameter
    raan_deg: Parameter
    argument_of_periapsis_deg: Parameter
    mean_anomaly_at_epoch_deg: Parameter
    epoch_utc: str
    frame: str
    propagator: str


@dataclass(frozen=True)
class Mode:
    id: str
    label: str
    default_pointing: str = "sun"
    description: str = ""
    diagram_x: float = 0.0
    diagram_y: float = 0.0

    @property
    def name(self) -> str:
        return self.label


@dataclass(frozen=True)
class LoadCapability:
    essential: bool = False
    shedding_priority: int = 100
    enabled: bool = True


@dataclass(frozen=True)
class GeneratorCapability:
    sunlight_dependent: bool = True
    enabled: bool = True


@dataclass(frozen=True)
class BatteryCapability:
    capacity_wh: Parameter
    initial_energy_wh: Parameter
    charge_efficiency: Parameter
    discharge_efficiency: Parameter
    max_charge_w: Parameter
    max_discharge_w: Parameter


@dataclass(frozen=True)
class ProducerCapability:
    destination_queue_id: str


@dataclass(frozen=True)
class ProcessorCapability:
    source_queue_id: str
    destination_queue_id: str
    output_input_ratio: Parameter
    retain_raw: bool = False


@dataclass(frozen=True)
class StorageCapability:
    usable_bytes: Parameter
    initial_queue_bytes: dict[str, Parameter] = field(default_factory=dict)


@dataclass(frozen=True)
class RadioCapability:
    supported_station_ids: tuple[str, ...]
    downlink_queue_id: str
    uplink_queue_id: str | None = None


@dataclass(frozen=True)
class ModeValues:
    """Resolved values; ``None`` means capability not present, not defaulted."""

    current_a: Parameter | None = None
    nominal_load_w: float = 0.0
    nominal_generation_w: float = 0.0
    active: bool | None = None
    idle_power_w: Parameter | None = None
    active_power_w: Parameter | None = None
    idle_current_a: Parameter | None = None
    active_current_a: Parameter | None = None
    generation_w: Parameter | None = None
    data_generation_bytes_per_s: Parameter | None = None
    processing_input_bytes_per_s: Parameter | None = None
    downlink_bps: Parameter | None = None
    uplink_bps: Parameter | None = None


@dataclass(frozen=True)
class Component:
    id: str
    name: str
    mass_kg: Parameter
    mode_values: dict[str, ModeValues]
    load: LoadCapability | None = None
    generator: GeneratorCapability | None = None
    battery: BatteryCapability | None = None
    producer: ProducerCapability | None = None
    processor: ProcessorCapability | None = None
    storage: StorageCapability | None = None
    radio: RadioCapability | None = None
    type: str = "custom"


@dataclass(frozen=True)
class AvailabilityInterval:
    start_utc: str
    end_utc: str


@dataclass(frozen=True)
class GroundStation:
    id: str
    name: str
    latitude_deg: Parameter
    longitude_deg: Parameter
    altitude_m: Parameter
    minimum_elevation_deg: Parameter
    effective_downlink_bps: Parameter
    effective_uplink_bps: Parameter
    supported_radio_ids: tuple[str, ...]
    availability: tuple[AvailabilityInterval, ...] = ()


@dataclass(frozen=True)
class DataQueue:
    id: str
    label: str


@dataclass(frozen=True)
class Defaults:
    initial_mode_id: str
    default_producer_queue_id: str
    default_processor_input_queue_id: str
    default_processor_output_queue_id: str
    default_downlink_queue_id: str
    default_uplink_queue_id: str
    retain_raw_after_processing: bool = False


@dataclass(frozen=True)
class DeleteRequest:
    queue_id: str
    bytes: Parameter


@dataclass(frozen=True)
class Actions:
    """Requests from a controller; ``None`` preserves current overrides."""

    mode_id: str | None = None
    pointing: str | None = None
    processing_enabled: bool | None = None
    downlink_enabled: bool | None = None
    reset_overrides: bool = False
    delete_requests: tuple[DeleteRequest, ...] = ()


@dataclass(frozen=True)
class ScheduleInterval:
    actions: Actions
    start_elapsed_s: Parameter | None = None
    end_elapsed_s: Parameter | None = None
    start_utc: str | None = None
    end_utc: str | None = None


@dataclass(frozen=True)
class Condition:
    """One comparison or an ``all``/``any``/``not`` condition tree."""

    kind: str
    field: str | None = None
    op: str | None = None
    value: Any = None
    queue_id: str | None = None
    children: tuple[Condition, ...] = ()


@dataclass(frozen=True)
class BlockRule:
    condition: Condition
    actions: Actions


@dataclass(frozen=True)
class ControlConfig:
    type: str = "none"  # none, python, schedule, blocks
    script_path: str | None = None
    script_source: str | None = None
    intervals: tuple[ScheduleInterval, ...] = ()
    rules: tuple[BlockRule, ...] = ()
    fallback: Actions | None = None


@dataclass(frozen=True)
class ResolvedConfiguration:
    schema_version: int
    project: ProjectInfo
    simulation: SimulationConfig
    orbit: OrbitalElements
    modes: tuple[Mode, ...]
    components: tuple[Component, ...]
    ground_stations: tuple[GroundStation, ...]
    data_queues: tuple[DataQueue, ...]
    control: ControlConfig
    defaults: Defaults
    defaults_applied: tuple[str, ...] = ()
    electrical_bus_voltage_v: Parameter | None = None
    transitions: tuple[TransitionDefinition, ...] = ()
    # Original dictionary is retained to allow unmodified, lossless save/reload.
    original: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def states(self) -> tuple[Mode, ...]:
        return self.modes


@dataclass(frozen=True)
class SatelliteState:
    """Committed resource state, separate from configuration and actions."""

    time_utc: str
    elapsed_seconds: float
    mode_id: str
    pointing: str
    battery_energy_wh: float
    queue_bytes: Mapping[str, float]
    processing_enabled: bool | None = None
    downlink_enabled: bool | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "queue_bytes", MappingProxyType(dict(self.queue_bytes)))


@dataclass(frozen=True)
class Status:
    """Read-only controller input at a simulation interval boundary."""

    time_utc: str
    elapsed_seconds: float
    mode_id: str
    seconds_in_mode: float
    battery_energy_wh: float
    battery_percent: float
    storage_used_bytes: float
    storage_capacity_bytes: float
    queue_bytes: Mapping[str, float]
    downlink_queue_bytes: float
    position_eci_m: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    in_eclipse: bool
    visible_ground_stations: tuple[str, ...]
    ground_station_visible: bool
    available_downlink_bps: float
    previous_generation_w: float = 0.0
    previous_consumption_w: float = 0.0
    previous_unmet_load_w: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "queue_bytes", MappingProxyType(dict(self.queue_bytes)))


@dataclass(frozen=True)
class TransitionDefinition:
    """Ordered transition data only; priority ties use declaration order."""

    id: str
    source_state_id: str
    target_state_id: str
    condition: Condition
    priority: int = 0
    minimum_dwell_seconds: Parameter = field(
        default_factory=lambda: Parameter(0, "s", is_default=True)
    )


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"


# State/mode terminology is unified without duplicating configuration objects.
ProjectConfig = ResolvedConfiguration
ResolvedProjectConfig = ResolvedConfiguration
StateDefinition = Mode
ComponentConfig = Component
OrbitConfig = OrbitalElements
GroundStationConfig = GroundStation
@dataclass(frozen=True)
class ActionRequest:
    """Controller request; omitted fields preserve current overrides."""

    state_id: str | None = None
    pointing: str | None = None
    processing_enabled: bool | None = None
    downlink_enabled: bool | None = None
    reset_overrides: bool = False
    delete_requests: tuple[DeleteRequest, ...] = ()


@dataclass(frozen=True)
class SatelliteSnapshot:
    time_utc: datetime
    elapsed_seconds: float
    state_id: str
    seconds_in_state: float
    battery_energy_wh: float
    queue_bytes: Mapping[str, float]
    transmitted_total_bytes: float
    rejected_total_bytes: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "queue_bytes", MappingProxyType(dict(self.queue_bytes)))


@dataclass(frozen=True)
class EnvironmentSnapshot:
    time_utc: datetime
    position_eci_m: tuple[float, float, float]
    latitude_deg: float
    longitude_deg: float
    altitude_m: float
    in_eclipse: bool
    visible_station_ids: tuple[str, ...]
    selected_station_id: str | None
    available_downlink_bps: float


@dataclass(frozen=True)
class PowerLedger:
    """Interval-integrated bus energies in Wh, keyed by stable component ID.

    Battery change is positive for stored energy gain. Losses are nonnegative.
    No allocation or integration is performed by this data object.
    """

    requested_wh: Mapping[str, float]
    generated_wh: Mapping[str, float]
    served_wh: Mapping[str, float]
    curtailed_wh: Mapping[str, float]
    battery_change_wh: float
    losses_wh: float

    def __post_init__(self) -> None:
        for name in ("requested_wh", "generated_wh", "served_wh", "curtailed_wh"):
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True)
class DataLedger:
    """Interval byte flows and ending occupancy, each keyed by queue ID.

    Processed input and output are separate to expose compression/retention.
    Rejected bytes are excluded from accepted bytes and onboard occupancy.
    """

    generated_bytes: Mapping[str, float]
    accepted_bytes: Mapping[str, float]
    rejected_bytes: Mapping[str, float]
    processed_input_bytes: Mapping[str, float]
    processed_output_bytes: Mapping[str, float]
    transmitted_bytes: Mapping[str, float]
    deleted_bytes: Mapping[str, float]
    ending_queue_bytes: Mapping[str, float]

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, MappingProxyType(dict(getattr(self, name))))


@dataclass(frozen=True)
class SimulationEvent:
    time_utc: datetime
    elapsed_seconds: float
    category: str
    explanation: str
    component_id: str | None = None
    queue_id: str | None = None


@dataclass(frozen=True)
class IntervalResult:
    next_snapshot: SatelliteSnapshot
    power_ledger: PowerLedger
    data_ledger: DataLedger
    events: tuple[SimulationEvent, ...]
