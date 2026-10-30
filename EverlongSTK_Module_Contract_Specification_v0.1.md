# EverlongSTK — Module Contracts and GUI Specification

**Version:** 0.1 (development contract)  
**Date:** 2026-10-30  
**Status:** Proposed baseline for independent module development  
**Primary language:** Python 3.13  
**GUI:** PySide6 / Qt Widgets  
**Development environment:** Nix flake in the Git repository

## 0. Authority, inputs, and scope

This document turns the proposed *EverlongSTK Specification v0.2* and the latest *EverlongSTK HTML mockup* into explicit module interfaces and acceptance criteria. Both are included under `docs/reference/` in the starter repository.

**Precedence when requirements appear to conflict:**

1. The latest HTML mockup is the **visual and interaction reference** for the three main pages and their controls. Preserve its conventional, minimally styled appearance.
2. The v0.2 specification is the **engineering and accounting reference** for conservation, orbital assumptions, time semantics, run lifecycle, reproducibility, and physical limits.
3. This document defines the integration contracts and resolves the differences needed to implement the real application. Conflicts that remain unresolved are explicitly listed in Section 15, not silently inferred.

The prototype contains illustrative orbits, power behavior, contact windows, and simplified data storage logic. **None of those demonstrations are reference physics outputs.** The real implementation must substitute validated model outputs without redesigning the interface.

### Goals

- A local, native, understandable satellite budget simulator, with GUI and headless CLI using the same engine.
- Independently developed and tested modules, integrated incrementally in a **single repository** and **single Python package**.
- Understandable approximate calculations with visible units, assumptions, provenance, hard physical limits, and documented accuracy limits.
- Robust multi-orbit and seasonal studies, including two-year runs with bounded memory and streaming persistence.
- An interface close enough to the HTML mockup that an operator immediately recognizes the same layout and workflow.

### Non-goals for the first release

Accounts, hosted services, 3D globe animation, spacecraft attitude dynamics, RF link budgets, thermal models, battery aging, full-fidelity flight dynamics, an arbitrary expression evaluator, a plugin framework, distributed simulation, or freely editable conservation equations.

---

## 1. Architectural rules

1. **One modular monolith.** Modules are ordinary Python files inside `everlong_stk`; they are not separately installable packages or services.
2. **One-way dependencies.** `gui` and `cli` can call application lifecycle functions; the engine must never import `gui`, Qt, matplotlib, pyqtgraph, or sqlite3.
3. **Shared models live in `models.py`.** Cross-module objects use typed, small, documented frozen data classes; avoid undocumented dictionaries across interfaces.
4. **Explicit units.** Public attributes have unit suffixes (`_wh`, `_w`, `_bytes`, `_bps`, `_seconds`, `_deg`, `_m`) unless the quantity is dimensionless.
5. **Deterministic calculations.** No use of wall-clock time, random numbers, threads, GUI state, or network data inside a simulation step. Orbit constants, epoch, propagator and assumptions are inputs.
6. **Simulation state belongs to the core.** The GUI may retain unsaved edit buffers and plot settings but cannot independently calculate or mutate resource balances.
7. **Model validation is authoritative.** GUI field checks improve usability but do not replace configuration validation.
8. **Physical resource limits always win.** Policies request actions; they cannot override energy, power, storage, or link constraints.
9. **Results are append-only per run.** Each run owns an immutable configuration snapshot and its own SQLite file.
10. **Avoid speculative abstractions.** Start with functions and data classes, introduce a class only for a concrete stateful responsibility, and keep Qt widget subclasses UI-only.

### Supported target platforms

Development: macOS Apple Silicon (`aarch64-darwin`) and Linux (`x86_64-linux`, `aarch64-linux`). Windows is a possible non-Nix deployment target, not a promised tested Nix platform. GUI, WebEngine, and Qt plugin behavior must be smoke-tested on each supported OS before claiming it works.

---

## 2. Module boundaries and ownership

| Unit | Owns | May depend on | Must not depend on |
|---|---|---|---|
| `models.py` | Shared data classes, enums, named units, immutable step/result contracts | stdlib | Every other EverlongSTK module |
| `configuration.py` | JSON schema versioning, parse/resolve defaults, validation, provenance, save/load | models | GUI, engine, SQLite |
| `orbit.py` | Propagation, Sun direction, eclipse, Earth rotation, station access | models, numeric libs | Control, power, data, GUI, SQLite |
| `control.py` | Deterministic ordered state transitions, schedule adapter, optional trusted Python policy, Python preview | models | Orbit implementation, power implementation, GUI |
| `power.py` | Bus generation, served/unserved loads, battery allocation and energy ledger | models | Data, orbit implementation, GUI, SQL |
| `data.py` | Producers, queues, processing, accepted/rejected data, powered radio transmission and ledgers | models | Power implementation, orbit implementation, GUI, SQL |
| `simulation.py` | Interval ordering, event splitting, calls to modules, atomic state commit | models, orbit, control, power, data | GUI, SQL, plots |
| `lifecycle.py` | Start/pause/resume/cancel/restart orchestration and run progress | simulation, results, configuration | Qt (generic core lifecycle) |
| `results.py` | SQLite schema, single-writer batch append, bounded queries, exports | models, stdlib sqlite3 | GUI, simulation calculation details |
| `reporting.py` | CSV/report/plot preparation from saved data | results, matplotlib if needed | GUI implementation |
| `cli.py` | Headless commands and user-readable errors | lifecycle, configuration, reporting | Qt |
| `gui/*` | Tabs, widgets, state diagram, map, plots, worker, presentation | core public API, PySide6 | Direct mutation of core state or SQL writes |

**Development rule:** A module owner may add private helpers and internal tests, but proposed changes to shared model objects, public function signatures, serialization schema, calculation order, or canonical units require review by the integration owner.

---

## 3. Proposed repository layout

```text
everlongstk/
├── flake.nix
├── flake.lock                 # generate with nix flake lock; commit to Git
├── pyproject.toml
├── README.md
├── .gitignore
├── docs/
│   ├── module_contracts_v0.1.md
│   ├── architecture.md         # later: decisions and diagrams
│   ├── equations.md            # later: exact physics and data equations
│   └── reference/
│       ├── specV2.md
│       └── everlongstk_mockup.html
├── examples/
│   └── generic_cubesat.json   # validated sample, implemented in phase 1
├── src/everlong_stk/
│   ├── __init__.py
│   ├── __main__.py
│   ├── models.py
│   ├── configuration.py
│   ├── orbit.py
│   ├── control.py
│   ├── power.py
│   ├── data.py
│   ├── simulation.py
│   ├── lifecycle.py
│   ├── results.py
│   ├── reporting.py
│   ├── cli.py
│   └── gui/
│       ├── __init__.py
│       ├── app.py
│       ├── main_window.py
│       ├── configuration_tab.py
│       ├── simulation_tab.py
│       ├── results_tab.py
│       ├── state_diagram.py
│       ├── map_view.py
│       └── worker.py
└── tests/
    ├── test_configuration.py
    ├── test_orbit.py
    ├── test_control.py
    ├── test_power.py
    ├── test_data.py
    ├── test_simulation.py
    ├── test_results.py
    └── test_gui.py
```

Do not generate an empty file for every suggested module simply to satisfy the tree: add files in their implementation phase. The included starter provides only bootstrap code, not a functioning engine.

---

## 4. Shared model and unit contract (freeze before parallel work)

**Canonical units used *inside* the model:** UTC-aware datetimes; elapsed and interval time in seconds; position in meters in a documented ECI frame; altitude in meters; angles in degrees; mass in kg; battery energy in Wh; electrical bus power in W; configured current in A; data amounts in bytes; production/processing in bytes/s; radio rates in bits/s.

**UI conversions:** `1 MB = 1,000,000 bytes`, `1 Mbit/s = 1,000,000 bits/s`, `1 km = 1,000 m`; never use binary MB or silently change units. Use floating-point byte amounts for the v0.2 *divisible-volume* approximation, and preserve balance to a documented numerical tolerance; do not round at every step. CSV exports always include units in column names.

### 4.1 Configurations

- `ProjectConfig`: `schema_version`, project ID/name/description, `SimulationConfig`, `OrbitConfig`, states, transitions/controller, components, stations, queue definitions, and defaults.
- `SimulationConfig`: `epoch_utc`, `duration_seconds`, `calculation_step_seconds` (default 20), `output_interval_seconds` (must be >= calculation step), orbital model constants and an explicit output policy.
- `OrbitConfig`: semi-major axis, eccentricity, inclination, RAAN, argument of periapsis, mean anomaly, frame and propagator choice; advanced fields can be hidden initially but must have visible documented defaults.
- `StateDefinition`: stable `id`, editable `name`, description, diagram coordinates (presentation-only), default pointing/flags.
- `TransitionDefinition`: stable ID, source state ID, target state ID, structured condition, priority/order, optional hysteresis/dwell; fallback stays in current state unless a chosen policy defines otherwise.
- `ComponentConfig`: stable `id`, name/type, mass, capability flags, optional hardware capacities, per-state current set, per-state data-generation set, radio parameters, essential/priority metadata, provenance.
- `GroundStationConfig`: stable ID, latitude, longitude, altitude, minimum elevation, supported radio IDs, availability and effective link rates.

Stable IDs, not human-readable labels or row numbers, are used in references. Renaming a state does not invalidate component settings or transitions. Adding a state requires explicitly filling every required per-state input; an empty field is **not** silently zero.

### 4.2 Runtime snapshots and request/response objects

The following names describe the planned **public contracts**, not implemented code:

```python
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
    # cumulative ledgers and previous-interval flows as needed

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
class ActionRequest:
    state_id: str | None = None
    pointing: str | None = None
    processing_enabled: bool | None = None
    downlink_enabled: bool | None = None
    # explicit, one-time deletion requests may be added

@dataclass(frozen=True)
class IntervalResult:
    next_snapshot: SatelliteSnapshot
    power_ledger: PowerLedger
    data_ledger: DataLedger
    events: tuple[SimulationEvent, ...]
```

Mapping fields must be treated as immutable (copy on creation / read-only exposure). A `PowerLedger` records requested/generated/served/curtailed energy or power per component and losses. A `DataLedger` records producer input, accepted, rejected, processed, transmitted, and explicitly deleted data, plus per-queue occupancy. Every event has UTC/elapsed time, a category, component/queue IDs where relevant, and an explanation.

### 4.3 Current and generator semantics

The HTML input convention is kept: each component has a **required signed current in A for every state**. Positive means consumption, zero is explicitly zero, and negative means generation. The UI also exposes the configured **electrical bus voltage**, as in the mockup.

- At configuration resolution, nominal power is `power_w = bus_voltage_v * current_a`.
- The core separates generation (`max(-power_w, 0)`) from load (`max(power_w, 0)`); it never treats a negative load as a way to bypass allocation.
- Negative current is only allowed on a component with the generator capability (including explicitly marked custom generators). Other negative currents fail validation.
- Sun-dependent generators provide zero generation during eclipse; pointing alone does not scale generation in this version.
- Configured per-state values are requested/nominal values. Actual served power depends on hardware limits, available generation and battery energy. Conditional components such as radios/processors require explicit idle behavior; the corresponding advanced idle-power fields/default indicators must be implemented before asserting v0.2 parity.
- Battery capacity is stored in Wh, **not** in Ah. The default initial Wh, efficiencies, and maximum charge/discharge bus powers remain separate battery inputs.

### 4.4 Data capability semantics

- `Generates data` checkbox enables **a required nonnegative byte/s value for every state**; no generation is allowed when unchecked.
- `Data capacity relevant` marks a storage component and its physical capacity. The first release supports exactly **one physical storage device**, shared by logical queues. The model rejects multiple physical storage owners rather than silently adding capacities.
- `Battery / energy storage relevant` similarly identifies exactly **one battery** for the first release.
- `Ground link relevant` enables effective radio rate and a minimum ground-station elevation. The selected contact must also satisfy station-level limits, availability, and compatibility.
- Generation is credited only if the producer was actually supplied power; transmission is credited only if the radio was powered, a compatible contact exists, and eligible data was present.
- Data sent to the ground is removed from the appropriate queue **only after the same amount is counted successfully downlinked**. Queue occupancy never becomes negative or exceeds shared capacity.
- Excess generated data rejected for lack of capacity increments a separate, persistent lost-data counter.
- Preserve v0.2's `raw` and `processed` logical queues and optional processing/compression. The GUI can show **aggregate storage**, with advanced queue details later; do not replace the accounting model with a single unexplained data counter.

---

## 5. Public module interfaces

The following signatures are proposals. Owners can add private functions without interface review; changes here require an integration review and tests.

### 5.1 Configuration (`configuration.py`)

```python
def load_project(path: Path) -> ProjectConfig: ...
def validate_project(config: ProjectConfig) -> tuple[ValidationIssue, ...]: ...
def resolve_project(config: ProjectConfig) -> ResolvedProjectConfig: ...
def save_project(path: Path, config: ProjectConfig) -> None: ...
def export_component_table(config: ProjectConfig, target_csv: Path) -> None: ...
```

`resolve_project` returns applied defaults and provenance without mutating the input. Invalid units, missing per-state values, invalid state references, nonfinite values, impossible capacities or negative data rates are errors. Explicit zero survives JSON round-trips and default resolution. Component CSV has row number, stable ID, name, type, mass, relevance flags and capacities, signed current for **each** state, data-generation enable/rate for **each** state, and link properties.

### 5.2 Orbit/environment (`orbit.py`)

```python
def evaluate_environment(config: ResolvedProjectConfig, time_utc: datetime) -> EnvironmentSnapshot: ...
def find_environment_boundaries(config: ResolvedProjectConfig, start_utc: datetime, end_utc: datetime) -> tuple[datetime, ...]: ...
```

Initial physics: elliptic Kepler propagation, documented optional secular J2 correction, **date-dependent** Sun vector, Earth rotation, geometric binary eclipse, and geometric station elevation. Correctly select an effective compatible radio/station link, using the minimum of satellite and station effective rates. The model never invents future contact windows from map animation. Validate against independent orbit and contact references and document fidelity limits.

### 5.3 State control (`control.py`)

```python
def decide_actions(config: ResolvedProjectConfig, snapshot: SatelliteSnapshot, environment: EnvironmentSnapshot) -> ActionRequest: ...
def validate_transitions(config: ProjectConfig) -> tuple[ValidationIssue, ...]: ...
def preview_python(config: ProjectConfig) -> str: ...
```

Visual rules are structured data. **Top-to-bottom, first matching transition wins**; preserve a clear fallback. Test battery thresholds, contact-and-queued-data conditions, eclipse/sunlight, and minimum dwell to prevent unintended thrashing. The generated Python is a human-readable preview, **not** a second independently maintained controller. Later, schedule and trusted local Python adapters implement the same `ActionRequest` contract; only one controller is active per run.

### 5.4 Power (`power.py`)

```python
def allocate_power(config: ResolvedProjectConfig, snapshot: SatelliteSnapshot, environment: EnvironmentSnapshot, actions: ActionRequest, interval_seconds: float) -> PowerResult: ...
```

`PowerResult` includes actual powered activities per component, next battery energy and an explicit ledger. Serve loads from generation first, then allowed battery discharge, charge battery only from surplus subject to efficiencies and bus limits, and record curtailment/unserved demand. Essential loads, shedding priorities and stable tie-breaking follow v0.2. No negative energy and no generation during eclipse for solar-dependent sources.

### 5.5 Data (`data.py`)

```python
def advance_data(config: ResolvedProjectConfig, snapshot: SatelliteSnapshot, environment: EnvironmentSnapshot, actions: ActionRequest, powered: PoweredActivities, interval_seconds: float) -> DataResult: ...
```

`DataResult` includes updated queue occupancy, cumulative transmitted/rejected data and a ledger. v0.2 ordering within an interval: **downlink previously eligible data → process existing input → accept newly generated/uplink data**. Newly generated input is processable next interval; newly processed output is downlinkable next interval. Correctly limit radio bit/s into bytes/s and apply available contact time. Explicit deletion actions are logged separately from transmitted bytes. Never count data as successfully delivered if a link is unavailable or an activity is unpowered.

### 5.6 Simulation coordinator (`simulation.py`)

```python
def advance_interval(config: ResolvedProjectConfig, snapshot: SatelliteSnapshot, nominal_step_seconds: float) -> IntervalResult: ...
def iterate_run(config: ResolvedProjectConfig, initial_snapshot: SatelliteSnapshot) -> Iterator[IntervalResult]: ...
```

The coordinator chooses event/nominal-step/output boundaries, invokes environment, control, power allocation and data accounting in deterministic order, then **commits one consistent state**. Neither `power.py` nor `data.py` mutates the snapshot or writes to SQLite. At resource bounds, the interval must split and reallocate rather than allow impossible activity for the rest of a step. Any zero-length event loops are guarded against. The coordinator has no Qt imports and can run headless.

### 5.7 Run lifecycle (`lifecycle.py`)

```python
class RunSession:
    def start(self, config: ResolvedProjectConfig, output_path: Path) -> RunId: ...
    def request_pause(self) -> None: ...
    def request_resume(self) -> None: ...
    def request_cancel(self) -> None: ...
    def progress(self) -> RunProgress: ...
```

States: `created`, `running`, `pause_pending`, `paused`, `completed`, `cancelled`, `failed`. Pause/cancel are acknowledged at committed boundaries; do not show paused before acknowledgment. Project edits during a run do not change its snapshot. Edits during pause require restart or explicit draft discard before resume. Stop preserves partial results. Restart creates a distinct run. A GUI worker uses Qt signals **outside** this pure lifecycle module.

### 5.8 Results/reports (`results.py`, `reporting.py`)

```python
def create_run_file(path: Path, metadata: RunMetadata) -> RunWriter: ...
def append_committed_batch(writer: RunWriter, batch: Sequence[IntervalResult]) -> None: ...
def get_samples(path: Path, start_seconds: float, end_seconds: float, max_points: int) -> SampleBatch: ...
def get_events(path: Path, filters: EventFilters) -> tuple[SimulationEvent, ...]: ...
def export_timestep_components(path: Path, target_csv: Path) -> None: ...
def export_run_report(path: Path, target_file: Path) -> None: ...
```

One SQLite file per run, one writer connection owned by its worker, separate GUI reader connection, bounded transactions and bounded plot queries. Persist immutable configuration (original/resolved, default flags, policy text/hash), engine/dependency/schema versions, samples, optional component samples, queue samples, events, and between-sample min/max summaries. Always store initial/final states and limit events. Exports stream rather than loading years of samples into RAM. Saved runs may be reopened for inspection and run comparison.

---

## 6. Simulation interval and timing contract

1. Read committed state at time `t`.
2. Evaluate environment and build read-only controller status.
3. Evaluate active controller, validate actions, apply requested state/pointing/flags and explicit deletions.
4. Select earliest next boundary (nominal step, schedule change, contact/eclipse crossing, output boundary, resource bound, or run end).
5. Determine requested component activity/power/data flow.
6. Allocate available electrical power, with essential/priority shedding and idle fallback.
7. Use **actual powered activity** to compute data downlink, processing, data production, queue acceptance and loss.
8. Integrate/commit battery energy and queue/counter state together.
9. Persist sampled results and events as applicable; advance time.

**Three independent concepts:** Calculation step (default 20 s, physically meaningful), saved output interval (>= nominal calculation step), and GUI playback speed / refresh interval (presentation only). Changing playback speed must not alter simulated results. Changing calculation step during a run requires a new run and new immutable config. Step backward reads previously committed/sampled states; it never reverses the physics engine. The mockup's 5 s demo data sampling is not the real engine's calculation interval.

At 20 s steps, a two-year case is roughly 3.15 million nominal intervals before event splitting. No code should cache every rendered snapshot or every plot point in RAM.

---

## 7. GUI parity contract: PySide6 should resemble the HTML reference

### Layout and style rules

- Exactly **three top-level tabs** in a single `QTabWidget`, in this order, horizontally across the top: **Configuration | Simulation | Results**. Do not replace them with a sidebar or the v0.2 split-pane workspace.
- Match the mockup's information grouping, field order, labels, default values, and basic density. Use ordinary Qt controls and system/default font and colors; only simple borders/panel dividers and functional status colors.
- Use vertical scroll areas for long tabs. Allow sensible window resizing. Preserve numerical field precision and show units beside entries. Use standard dialogs for validation and file operations.
- Treat the HTML as a visual reference and parity checklist, **not as application runtime code**. Domain calculations remain in Python.

### Tab 1 — Configuration

**Section 1: Orbit parameters**

| Field | Default reference | Notes |
|---|---|---|
| Semi-major axis | 6,928.137 km | No orbit-type dropdown |
| Eccentricity | 0 | Dimensionless |
| Inclination | 97.5 deg | |
| UTC epoch | 2027-01-01 00:00 UTC | Explicit UTC timezone |
| Ground station latitude | 63.4 deg | Initial sample |
| Ground station longitude | 10.4 deg | Initial sample |
| Electrical bus voltage | 5 V | Used to resolve signed current to nominal power |

Further orbit and station parameters from v0.2 (RAAN, argument, mean anomaly, station altitude/rates/availability, propagator) should be available through an **Advanced** expander or clearly documented defaults rather than silently omitted.

**Section 2: Satellite states and state diagram**

- Initial four state labels and meanings: **Idle** (awake/ready), **Capturing data** (payload active), **Transmit / receive** (ground communications), **Survival** (low-power recovery).
- Native editable diagram with draggable rectangular nodes, arrow connectors, an add-state action, state name/description table, ordered transition table and add-transition action.
- First matching transition has priority; fallback remains in current state. Validation identifies invalid/missing target/source and rule thresholds.
- Show a **Compile to Python (preview)** and **Copy Python** control; the preview is read-only and has no execution effect on the visual controller.
- Preserve diagram positions in the project file as UI metadata, not satellite dynamics.

**Section 3: Satellite components**

- Type selector: Battery, Solar panels, On-board computer, Camera/payload, Radio/transceiver, Antenna, Storage device, ADCS, MQTT module, Processor, GNSS receiver, **Custom component**.
- Add/remove/edit name, type, and mass. Per-component checkbox: **Battery / energy storage** with capacity Wh; **Data capacity relevant** with capacity MB; **Ground link relevant** with minimum elevation and effective downlink; **Generates data** with required data-generation rate in MB/s for **every** state.
- Every component has required signed **current draw in A for every state**, negative only for enabled generators. Distinguish explicit zero from missing.
- Component table preview and **Export component table (.csv)**, with exactly one row per component and dynamic columns for added/renamed states. Include battery/data/link relevance, mass, capacities, all state currents and data generation rates.
- The real application's validation feedback must be at least as visible as the mockup's incomplete-field indicators.

### Tab 2 — Simulation

**Header controls:** Step backward, Play/Pause toggle, Step forward, Stop, Reset, simulation-speed slider, calculation timestep slider/input, elapsed simulated time, and completed-orbit counter. Timestep editing is disabled while an active run is locked; adjust/restart for the next run. Keep the controls and their relative positioning close to the HTML reference.

**Middle Earth map:** Real geographic boundaries with plotted satellite ground position, illustrative station marker(s), and a ground track. Feed the map from `EnvironmentSnapshot` and persisted results. Use a `MapView` abstraction: preferred implementation is Leaflet within Qt WebEngine if the bindings/platform are supported, with a **native/offline fallback** that can still show geographical outlines, station and satellite coordinates. Online map tiles must be optional; handle licensing, connectivity and tile usage policies. The map may not manufacture simulation positions.

**Bottom-left: Live satellite statistics:**

- Current satellite state, **battery percentage and fill meter**, net power.
- **Onboard storage used / capacity / percentage meter**, free capacity, empty/full indication.
- Component-level current draw/generation bars (including generator sign and actual served power); component-level **data generation** rates.
- Data generated, accepted storage write rate, storage read/deletion, ground link/contact, downlink send rate, ground received rate, cumulative transmitted total, **transmitted this orbit**, cumulative rejected data and cumulative generated data.
- Time-synchronized values come from committed snapshots/ledgers, never from the rendering timer.

**Bottom-right: Current state in diagram:** Same states and arrows as in Configuration, displayed read-only. **Highlight the current state with a thicker border and distinct fill**. Update on every committed playback frame.

### Tab 3 — Results

- Open/import a saved run in the application's own reproducible format (SQLite run with embedded immutable configuration/metadata). Export a run for reuse; **do not describe mockup JSON as the actual reproducible run format**. Export project JSON separately.
- Export a human-readable run report (HTML initially; PDF optional later).
- Export component configuration table CSV.
- Export component states/values **for each saved timestep** as streaming CSV (explicitly label that sampled outputs may be coarser than calculation steps; offer full-step capture only if configured, with performance warning).
- Checkboxes to show/export time plots: available/generated power, net charge/usage power, data capture rate, data downlink rate, cumulative transmitted data, onboard storage used, cumulative rejected data. Also meet v0.2 required battery Wh/%, requested/served power, queue plots and state timeline through expandable result sections.
- All plots use elapsed simulation time or UTC on x-axis; **mark completed orbits**; provide unit labels, pan/zoom/inspect, and restore-range. Long histories use bounded aggregate queries while preserving min/max and events.
- Show run metadata and summary, including assumptions, version, input snapshot, partial/failed status and validation warnings. Run comparison can follow after basic exports, using the same storage APIs.

### Visual acceptance procedure

A reviewer opens `docs/reference/everlongstk_mockup.html` beside the running PySide6 GUI and verifies: tab order, three Configuration sections, state diagram editing and highlighting, component fields with all states, geographic map and controls, battery and storage telemetry, component current/data bars, plots and export controls. Differences must be listed and approved; stylistic redesign is out of scope.

---

## 8. Project file and run-file contracts

### JSON project (`schema_version: 1`)

The JSON schema is owned by `configuration.py`. Conceptual top-level keys:

```json
{
  "schema_version": 1,
  "project": {"id": "generic_cubesat", "name": "Generic CubeSat"},
  "simulation": {"epoch_utc": "2027-01-01T00:00:00Z", "calculation_step_seconds": 20, "output_interval_seconds": 60},
  "orbit": {"semi_major_axis_m": 6928137, "eccentricity": 0, "inclination_deg": 97.5},
  "electrical_bus": {"voltage_v": 5.0},
  "states": [{"id": "idle", "name": "Idle"}],
  "transitions": [],
  "components": [],
  "ground_stations": [],
  "data_queues": [{"id": "raw"}, {"id": "processed"}],
  "control": {"type": "visual_rules"}
}
```

This is a **partial structural illustration, not yet a fully valid importable configuration**. Before phase 1 is accepted, create and freeze a complete validated example, including all required orbit elements, component fields, state currents, generation rates, and defaults/provenance. Never assume the mockup's exported JSON is schema-compatible; support an explicit conversion/import preview only after its mapping has tests.

### SQLite run (`results.py`)

Minimum persisted information: run ID/lifecycle/timestamps, schema and engine version, original + resolved input JSON and its SHA-256 hash, controller source/hash, constants/assumptions, `samples`, optional `component_samples`, `queue_samples`, `events`, and `interval_summaries`. Output snapshots must identify instant values versus interval-integrated flows. Partial/cancelled/failed data remains readable. SQLite schema changes require a version and a migration/read policy.

**No SQL in GUI, orbit, power, data or control modules.** Exports and plots use result query functions.

---

## 9. Run lifecycle and interactive behavior

- **Created/stopped:** user may edit, save, validate, start and inspect previous runs.
- **Running:** project inputs are locked; Play/Pause requests a pause; Stop requests cancellation; live statistics and plots remain inspectable.
- **Pause pending:** show an explicit pending status until the engine acknowledges a committed boundary.
- **Paused:** Step forward/backward refers to saved playback positions (not arbitrary reverse integration); same-run resume only when input snapshot remains unchanged.
- **Paused with edited draft:** display *Inputs changed — restart required*; Resume disabled until edits discarded.
- **Completed/cancelled/failed:** inspect, export, start a new run; Stop never silently resets or deletes old results; Reset returns the **view** to the start of its run. Restart makes a new run and preserves the previous one.
- **Speed slider:** presentation rate only. **Timestep slider:** new-run model calculation step; must not silently recompute or mutate a current run.

Worker process: initially one Qt worker thread for execution orchestration; only the GUI thread touches widgets. Qt signals convey bounded snapshots/progress. Worker owns SQLite writer, query side uses separate read connection. Move to process-based execution **only** if benchmarks demonstrate a thread responsiveness problem.

---

## 10. Minimum tests for independent development

| Unit | Required tests before merging |
|---|---|
| Configuration | JSON round-trip; explicit zero vs absent; stable IDs on rename; all per-state fields required; bad unit/rate/reference rejected; component CSV headers/units/dynamic states |
| Orbit | Circular period; coordinate transforms; date-dependent Sun; shadow crossing; geometry-based ground contact; deterministic station selection; reference-case comparisons |
| Control | First matching transition wins; fallback; threshold conditions; state rename; invalid transitions; equivalent rule/schedule/Python policy cases |
| Power | Hand-calculated constant generation/load, efficiencies, charge/discharge caps, shedding priority, essential load failures, zero and capacity bounds, eclipse solar zero |
| Data | Multiple producers; powered-only activity; full/empty storage; downlink removes exactly transmitted data; contact limits; 8 bits/byte; processed/raw queues; retention and compression; overflow rejected; integrated conservation |
| Coordinator | Correct call order, shared-state commit, event splitting, threshold reaction delay, end-of-run, repeatability, no zero-time loops |
| Results | Streamed large-run writes; reopened immutable metadata; partial failure; time-range queries/extrema; CSV/report consistency; schema version handling |
| GUI | Exact three tabs; no type selection in Orbit; state diagram drag/save/reload; all-state component inputs; correct meters; map marker from real snapshot; paused/edit locks; export UI |
| Platform/Nix | `nix develop`, Python imports, Qt offscreen widget smoke test, interactive display smoke test, headless CLI tests on target systems |

**Cross-module invariants, checked with integrated property/regression tests:**

- `0 <= battery_energy_wh <= capacity_wh` and `0 <= total_queue_bytes <= physical_storage_bytes` at every committed sample.
- Generated electrical energy, served load, battery change, losses and curtailment agree with the interval power ledger within a documented tolerance.
- `starting_stored + accepted_input + processed_net_change - downlinked - explicit_deleted = ending_stored` (using ledger conventions) within tolerance; rejected data not counted as stored.
- No data production, processing or transmission by a component whose required activity was not powered.
- A run with the same resolved inputs, controller, constants and engine version produces equivalent outputs within a documented numerical tolerance.
- GUI, CLI, CSV, stored SQL, plots, and reports agree on the same run's sampled values.
- Long runs keep peak RAM bounded; outputs retain between-sample extrema and limit events.

Tests include explicit hand-calculated fixture cases and independent reference comparisons, not self-generated expectations from the same algorithm being tested.

---

## 11. Independent work packages and integration gates

| Package | Depends on | Can start when | Hand-off artifact |
|---|---|---|---|
| A: Shared models and configuration | none | immediately | frozen interfaces, complete sample JSON, validation tests |
| B: Orbit/environment | A contracts | model types established | pure environment functions + reference tests |
| C: State machine/control | A contracts | model types established | structured rules evaluator, Python preview + tests |
| D: Power/battery | A contracts | model types established | pure allocation function and ledger + numerical tests |
| E: Data/storage | A contracts | model types established | pure accounting function and ledger + tests |
| F: Results/exports | A contracts | model types established | SQLite writer/reader/export APIs + tests |
| G: PySide6 GUI | A contracts and fake snapshots | immediately after contracts | visually faithful three-tab UI with stub data + UI tests |
| H: Coordinator/lifecycle/CLI | A, B–F public APIs (or stubs) | early integration skeleton | headless executable run and GUI adapter |

**Continuous integration, not big-bang integration:**

1. Build a minimal vertical slice early: sample JSON → fixed fake environment → fixed state → fake ledgers → coordinator → SQLite → CLI query → GUI meters.
2. Replace stubs one at a time with tested modules and add integration tests at each replacement.
3. Keep a known-good example run and automatic regression outputs checked in as small fixtures (not giant SQLite databases).
4. Require review for changes to public contracts, schema, units, step ordering, storage rules, or state-machine behavior.
5. Merge only when lint, unit tests, integration checks and headless CLI checks pass. GUI screenshot/manual parity is a distinct gate.

Milestones: (1) shell/repository/contract; (2) real headless power + data accounting; (3) orbit + control + integrated run; (4) results/SQLite/reporting; (5) faithful PySide6 UI; (6) long-duration, convergence and platform verification.

---

## 12. Nix flake development contract

- `flake.nix` is tracked in Git and defines `devShells.<system>.default` for Apple Silicon macOS and Linux, using a stable Nixpkgs branch. It manages Python, PySide6, NumPy, Matplotlib, PyQtGraph, pytest and Ruff; Python libraries come from one coherent Nixpkgs Python package set. Avoid mixing `pip install` wheels into Nix-managed Qt unless explicitly tested.
- `flake.lock` **must be generated by Nix and committed** before claiming reproducibility. It is **not fabricated** in this starter because Nix is not available in the authoring environment.
- Use `nix develop` to enter the environment. `python -m everlong_stk --help`, `python -m everlong_stk gui`, `python -m pytest` and `ruff check .` are the intended commands. The included code is only a bootstrapped placeholder.
- Keep normal `pyproject.toml` packaging so developers without Nix can still install the project, subject to platform-specific Qt requirements.
- Verify the Qt platform plugin and optional WebEngine bindings on both macOS and Linux before making WebEngine mandatory. The base GUI must still launch without an embedded web map.
- Nixpkgs version updates are deliberate reviewable pull requests: update `flake.lock`, run tests and interactive smoke tests, document breaking dependency changes.
- No software silently downloads map tiles or other runtime datasets during model calculations; map display requests are optional presentation activity.

### Bootstrap commands

```bash
git init
git add .
nix flake lock          # requires network and a functioning Nix installation
git add flake.lock
git commit -m "Initialize EverlongSTK architecture and Nix environment"
nix develop
python -m everlong_stk --help
python -m pytest
ruff check .
python -m everlong_stk gui
```

If `nix develop` reports an unavailable Qt/PySide6 derivation for a target platform, do not quietly install mismatched pip Qt libraries; first pin/adjust the Nixpkgs revision and verify the Python/Qt package set, then record the change. Do not mark that platform supported before a real GUI smoke test.

---

## 13. Code quality and maintainability rules

- Functions should have descriptive inputs and return values; use Python type hints for public interfaces and concise docstrings for assumptions, units and non-obvious decisions.
- Use `dataclasses` and the standard library by default; no microservice runtime, event bus, general dependency-injection framework, hidden metaclass registry or custom ORM.
- Core numerical code is separate from Qt signals, SQLite, and plotting.
- Use Ruff formatting/linting with a checked-in configuration and pytest tests near the behavior they verify.
- Document equations and physical constants in `docs/equations.md`, linked to test fixtures.
- Errors include component/field or simulated timestamp; failures do not destroy partial data.
- Don't optimize the numerical engine until benchmark data demonstrates the need. A functional baseline is more valuable than premature vectorization.

---

## 14. Acceptance criteria for this specification and the first GUI milestone

### Contract freeze (before parallel scientific development)

- [ ] Shared dataclasses, IDs, units, interval result, and component power/data semantics are reviewed.
- [ ] Complete example JSON loads, validates and round-trips without losing explicit zeros or defaults.
- [ ] Power and data accounting have independent hand-calculated baseline fixtures.
- [ ] A stub-based end-to-end run can be written, read and shown without integrating the real orbit/physics modules.

### GUI parity milestone

- [ ] Three top-level tabs named **Configuration**, **Simulation**, **Results**, arranged left/middle/right along the tab strip.
- [ ] Configuration has precisely the three principal sections from the HTML, **without an orbit-type dropdown**.
- [ ] State editor supports drag, add, rename, ordered transitions, validation and Python preview; the Simulation state diagram highlights the active node.
- [ ] Component editor supports all relevant checkboxes, current per state, generation rate per state, CSV preview/export and explicit missing-value validation.
- [ ] Simulation map displays geographically correct satellite coordinates and actual contact data from the environment API, with offline fallback.
- [ ] Battery and onboard-storage meters, per-component currents and data rates, accepted/rejected/transmitted counters update from committed results.
- [ ] Playback, pause acknowledgment, stop, reset, step navigation and slider semantics are correct.
- [ ] Results supports run reopen/export, component table export, timestep CSV, report and orbit-marked time plots with selectable series.
- [ ] Interface works at ordinary desktop sizes on tested macOS and Linux without special themes or web-server dependencies.

---

## 15. Decisions to verify before a stable v0.1 freeze

1. **Configured signed current and conditional idle consumption:** The HTML supplies a single current per state. The v0.2 model distinguishes idle and active power. Decide whether to expose an advanced idle field now (recommended) and define exact fallback behavior. Do not accidentally give inactive radios zero idle draw without a documented parameter.
2. **UI and core data processing:** v0.2 specifies raw → processed queues, processing and compression, while the mockup shows aggregate storage and directly transmitted captured data. Keep the raw/processed core contract; agree on default downlink queue/routing and whether the UI initially needs an advanced routing panel.
3. **Nix/Qt WebEngine availability:** Test current PySide6 WebEngine packaging on Apple Silicon and Linux; keep map adapter/fallback independent until verified.
4. **Numerical tolerance, time/event refinement and output sampling:** Record measured convergence of 20-second steps to finer reference cases; no generic accuracy claims.
5. **Actual two-year runtime targets:** Benchmark on the intended development machines, report wall time, memory, SQLite size and event volume.
6. **CLI commands and complete JSON/SQLite schemas:** Finalize during foundation phase using concrete working fixtures.
7. **State-machine transition logic:** Decide how mode hysteresis, minimum dwell, priority, and station contact enter the editable rule model while retaining the simple HTML diagram UI.

**Contract change policy:** Any modification to physical accounting, controller semantics, cross-module public types, JSON schema, SQLite schema or time semantics must update the relevant version and tests. UI presentation changes alone do not require a schema version change.

---

## 16. Original reference documents

- `docs/reference/specV2.md` — EverlongSTK proposed implementation specification v0.2, dated 2026-10-07.
- `docs/reference/everlongstk_mockup.html` — latest single-file Wizard-of-Oz mockup, including the data-generation/storage additions.

Suggested upstream documentation for contributors:

- Nix flakes: https://nix.dev/concepts/flakes
- Nixpkgs Python development: https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/python.section.md
- Nixpkgs Qt packaging: https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/qt.section.md
- Qt for Python: https://doc.qt.io/qtforpython-6/
