# EverlongSTK Specification

## Satellite Budget Simulator

Version: 0.2  
Date: 2026-10-07  
Status: proposed implementation specification

## 1. Purpose

Build a readable Python tool for exploring satellite designs by simulating battery energy levels, power consumption, stored data, processing, and communications over time. The first example is a generic CubeSat. The user decides what constitutes mission success; the tool reports states, bottlenecks, resource limits, and assumptions.

The primary use case is rapid satellite design prototyping. The primary users are academics and engineers planning satellite missions. Seasonal trade studies and simulations lasting two years support battery, solar-panel, storage, and communications sizing.

EverlongSTK is a budget simulation foundation for MBSE (Model-Based Systems Engineering) and mission planning, rather than a complete flight-dynamics system.

In organizations with frequent turnover of knowledge workers, simple software with visible assumptions can make concepts easier to test and hand over. The design prioritizes quick, understandable approximate calculations. Detailed engineering tools remain useful for subsequent validation and higher-fidelity analyses.

## 2. Product boundaries

- Python application launched from a Nix flake, with a native desktop GUI and a CLI for headless operation. Both use the same simulation engine and saved-run format.
- No browser interface, accounts, or hosted service in the MVP.
- Components have different operational values for each satellite mode. Four initial modes have labels A, B, C, D; labels are editable and additional modes are allowed.
- One satellite mode is active at a time. All component behavior is defined for each mode; missing optional values use documented defaults, visibly marked in the editor.
- Satellite control is selected from a schedule, a Scratch-inspired visual block editor, or a custom Python script. All three use the same status/action contract.
- The visual editor supports ordered conditions and actions rather than arbitrary loops or general-purpose programming. It is part of the GUI scope and may follow the basic parameter-and-plot interface within implementation.
- User-entered solar generation per mode is zero during eclipse. Pointing is recorded; it does not implicitly change generation in this version.
- Hard physical limits always apply. Policies can select priorities, thresholds, processing, and deletion behavior, but cannot create energy or exceed storage capacity.
- Default calculation step is 20 seconds. Increasing it reduces temporal resolution; the GUI distinguishes it from saved output intervals and playback speed. Shorter internal intervals split at events.
- Use JSON for project definitions and SQLite for saved runs. SQL is confined to the result-storage module.
- Keep styling simple and prioritize readable configuration, visible equations, responsive operation, and useful engineering outputs.

## 3. Architecture and readability

Use an MVC (Model–View–Controller) architecture with straightforward modules:

| Layer      | Responsibility                                                                                                                                                                              |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Model      | Configuration, components, orbital environment, control policy, power/data accounting, simulation state, SQLite run storage                                                                 |
| View       | CLI summaries and exports; GUI main window, mode editor, block editor, embedded plots, and run browser. Both present model snapshots and validation results; neither owns simulation state. |
| Controller | CLI argument parsing and headless lifecycle; GUI button handlers, menu actions, dialog validation, and worker orchestration. Both call the same model API and lifecycle functions.          |

The engine must work without the GUI, plotting, or CLI. Prefer ordinary functions and small data classes. Use explicit arguments and return values, descriptive names, and units in field names. Avoid dependency-injection frameworks, generic plugin systems, metaclasses, and inheritance unless a concrete need emerges. Widget subclasses are acceptable when required by the GUI toolkit; they must not contain physics or accounting rules.

### 3.1 Proposed repository

```text
flake.nix
flake.lock
pyproject.toml
README.md
src/everlong_stk/
    configuration.py    # Parse, default, validate, save project input
    models.py           # Small shared data classes
    orbit.py            # Position, sunlight, station access
    policy.py           # Schedule, blocks, Python policy adapters
    power.py            # Energy and power accounting
    data.py             # Queue, processing, storage, link accounting
    simulation.py       # Calculation order and committed state
    lifecycle.py        # Shared run sessions, pause/resume/cancel
    results.py          # SQLite writer, queries, CSV export
    plots.py            # Shared plot data and figure construction
    cli.py              # Headless controller and terminal views
    gui/
        app.py          # GUI entry point
        main_window.py  # Main workspace and toolbar
        controller.py   # GUI actions calling shared model functions
        worker.py       # Background run and control handoff
        parameter_editor.py
        mode_editor.py
        control_editor.py
        block_editor.py
        results_view.py
        run_browser.py
examples/generic_cubesat/
    satellite.json
    policy.py
tests/
```

`power.py` and `data.py` return proposed state and accounting ledgers. `simulation.py` coordinates allocation before committing state. Neither module writes to SQLite. `lifecycle.py` exposes ordinary start/pause/resume/cancel functions shared by controllers; it must not import GUI code.

Use PySide6 as the proposed native GUI toolkit, NumPy for numerical work, Matplotlib for shared figures and embedded plots, and the standard library for JSON, SQLite, CLI parsing, and data classes. Pin dependencies and retain a Nix lockfile. Keep Qt imports inside the GUI package so headless operation does not require a display. Verify toolkit packaging and licensing during implementation. Keep simulation code OS-independent and provide ordinary Python installation instructions where Nix is unavailable.

### 3.2 Shared model API

Both controllers use the same operations: load/save/validate project; resolve defaults; start a run from an immutable input snapshot; request pause/resume/cancel; read progress and committed status; query results/events; export CSV; and prepare plot data. Define these as documented functions and small result objects, not a generic service framework.

Views can hold temporary edit buffers and presentation settings. The project configuration and committed simulation state remain model-owned. Validation is authoritative in the model even when a GUI widget performs an early check.

### 3.3 GUI workspace

Use a resizable left/right split. The left side contains editable inputs and equations; the right side shows simulation outputs. A shared toolbar contains New, Open, Save, Start, Pause/Resume, Stop, Restart, and Export. A status bar shows lifecycle, simulated time, calculation progress, and errors.

| Left-side tab | Contents                                                                                                               |
| ------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Parameters    | Components, hardware values, per-mode values, orbit, ground stations, queues, simulation duration/step/output interval |
| Modes         | Mode names and IDs, component activity, pointing defaults, initial mode                                                |
| Control       | Controller selector; schedule table, visual blocks, or Python script selection/editor                                  |
| Equations     | Read-only built-in equations, variable definitions, units, assumptions                                                 |

| Right-side tab    | Contents                                                                    |
| ----------------- | --------------------------------------------------------------------------- |
| Results           | Battery, power, data/storage plots and mode timeline with aligned time axes |
| Events            | Filterable constraints, shedding, data loss, mode transitions, failures     |
| Runs & Comparison | Saved run browser, metadata, input snapshots, selected-run comparison       |

Parameter fields show unit, value, certainty, and a visible default indicator. Notes, sources, and bounds are available through a compact details panel. Empty/default and explicit zero must be distinguishable. Components and stations support add/edit/remove; removal reports dependent references and requires the user to resolve them.

Plots support selecting series, zooming, inspecting values, and restoring the full time range. Graphs and timeline may be shown together. Query only the displayed time range and aggregate long histories while preserving extrema/events. A simple map/orbit playback is optional after the budget GUI works; 3D animation is outside the MVP.

### 3.4 Background computation

Run the engine in one worker thread initially. Only the GUI thread accesses widgets. Commands cross to the worker through a thread-safe queue or explicit synchronized flags; progress, committed snapshots, and errors return through signals. Send bounded updates, normally at most a few per second; do not emit every simulation step or load an entire two-year history into the GUI.

The worker owns its SQLite writer connection. GUI queries use a separate reader connection against committed data; configure bounded transactions and suitable concurrent reading. Never share a SQLite connection between threads. Model pause/cancel checks occur at committed interval boundaries. Plot refresh and exports also use bounded work; long exports may use a separate worker.

The simulation clock advances independently of GUI refresh or playback. If thread execution causes unacceptable responsiveness in benchmarks, move the worker to a process behind the same model API; do not redesign the accounting engine.

## 4. Project configuration

### 4.1 Top-level structure

| Field             | Contents                                               |
| ----------------- | ------------------------------------------------------ |
| `schema_version`  | Configuration format version                           |
| `project`         | ID, title, description                                 |
| `simulation`      | UTC epoch, duration, calculation step, output interval |
| `orbit`           | Propagator choice, frame, orbital elements             |
| `modes`           | Stable IDs, labels, default pointing                   |
| `components`      | Hardware capabilities and per-mode operational values  |
| `ground_stations` | Coordinates, visibility mask, availability, link rates |
| `data_queues`     | Raw/processed queues sharing physical storage          |
| `control`         | Exactly one controller type and its configuration      |
| `defaults`        | Initial mode, resource behavior, queue routing         |

IDs are stable and unique; labels are editable. Policies reference mode IDs, not labels. Missing optional values receive documented defaults; an explicit zero remains zero. Missing required geometry or an unknown reference fails validation. Validation produces a resolved configuration that shows every applied default.

### 4.2 Parameter metadata

Every user-entered numerical engineering parameter supports:

```json
{
  "value": 8.0,
  "unit": "W",
  "certainty": "specified",
  "note": "Illustrative input; replace with a component source",
  "source": null,
  "lower_bound": null,
  "upper_bound": null
}
```

Allowed certainty values: `guesstimate`, `calculated_estimate`, `specified`, `tested`. Certainty is provenance, not a probability distribution or invented error percentage. Bounds are optional and must contain the nominal value. Defaults retain `is_default` in the resolved configuration. Required units are checked; initially accept one documented canonical unit per field rather than implicit conversions.

### 4.3 Components and modes

A component has `id`, `name`, `mass_kg`, capabilities, hardware limits, and a `mode_values` mapping keyed by mode ID. Components can combine capabilities: a camera consumes power and produces data; a radio consumes power and transmits data.

| Capability | Configuration                                                                |
| ---------- | ---------------------------------------------------------------------------- |
| Load       | Idle/active power, active flag per mode, essential flag, shedding priority   |
| Generator  | Electrical generation in W per mode, sunlight dependency                     |
| Battery    | Capacity Wh, initial energy, charge/discharge efficiencies, bus power limits |
| Producer   | Generation bytes/s, destination queue                                        |
| Processor  | Input throughput bytes/s, output/input size ratio, source/destination queues |
| Storage    | Usable bytes, initial queue contents                                         |
| Radio      | Downlink/uplink bits/s per mode, supported stations, downlink queue          |

Mass and capacities are hardware properties. Active power, idle power, data rates, processing throughput, and generation are operational values per mode. A missing mode entry uses explicit documented component defaults and is flagged; it must not accidentally copy another mode.

For a load, select idle power when inactive and active power when active; do not add both. Disabled loads consume zero. Processing and radio active power apply only while doing work; otherwise use idle power. Generation is electrical bus power after the user’s assumed panel/converter losses. One battery and one physical storage device are supported initially; many queues may share storage.

## 5. Orbit and environment

Provide a circular-orbit convenience form and an advanced orbital-elements form. The resolved representation contains semi-major axis (m), eccentricity, inclination (deg), RAAN (deg), argument of periapsis (deg), mean anomaly at epoch (deg), UTC epoch, and a documented Earth-centered inertial frame.

Initial environment model:

- Elliptic Kepler propagation with a documented secular J2 correction option for long-term plane/orbit orientation trends. Record the selected model and constants.
- Date-dependent Sun direction; a fixed Sun vector is unacceptable for seasonal studies.
- Earth rotation for longitude and station access; consistent inertial/Earth-fixed transforms.
- A documented geometric eclipse approximation. MVP sunlight is binary; no partial-shadow power model.
- Ground-station elevation calculated from spacecraft and station positions.

Ground stations contain stable ID, latitude, longitude, altitude, minimum elevation, availability intervals, supported radio IDs, and effective uplink/downlink rates. Effective rates already include the user’s assumed RF, protocol, and weather losses. MVP does not infer throughput from antenna gain or transmitter power.

For overlapping contacts, use one radio link at a time and select the compatible station with highest effective rate, breaking ties by station ID. Link rate is the minimum of satellite and station effective rates. Uplink is recorded as received bytes into a configured queue when enabled; it is not a command-execution simulation.

This model supports seasonal projections under stated assumptions. It does not promise exact individual passes two years into the future. No global “99.5% accuracy” claim is made: errors must be assessed separately for position, contact/eclipsing times, energy, and data. Drag, detailed attitude, thermal dynamics, battery aging, and full RF link budgets are outside the MVP.

## 6. Control contract

### 6.1 Python policy

```python
from everlong_stk.models import Actions

def decide_actions(status):
    if status.battery_percent < 20:
        return Actions(mode_id="a")
    if status.ground_station_visible and status.downlink_queue_bytes > 0:
        return Actions(mode_id="d", pointing="ground_station")
    if status.in_eclipse:
        return Actions(mode_id="c")
    return Actions(mode_id="b")
```

The policy receives a read-only snapshot before the next interval. It returns requests, never directly changes energy, queues, or orbit. Scripts are trusted local Python code with the user’s permissions; the MVP does not claim to sandbox them. Copy script source into run metadata. Policies should be deterministic and avoid wall-clock time, network calls, random globals, and hidden state. Persistent policy memory is deferred.

| Status field                                                    | Meaning                                                    |
| --------------------------------------------------------------- | ---------------------------------------------------------- |
| `time_utc`, `elapsed_seconds`                                   | Current simulation time                                    |
| `mode_id`, `seconds_in_mode`                                    | Current operating mode and dwell time                      |
| `battery_energy_wh`, `battery_percent`                          | Stored energy and fraction of nominal capacity             |
| `storage_used_bytes`, `storage_capacity_bytes`                  | Shared physical storage                                    |
| `queue_bytes`, `downlink_queue_bytes`                           | Queue occupancy and selected downlink backlog              |
| `position_eci_m`, `latitude_deg`, `longitude_deg`, `altitude_m` | Position                                                   |
| `in_eclipse`                                                    | Current binary sunlight state                              |
| `visible_ground_stations`, `ground_station_visible`             | Current access                                             |
| `available_downlink_bps`                                        | Current effective link capacity, not future contact volume |
| `previous_generation_w`, `previous_consumption_w`               | Previous interval averages; initial values zero            |
| `previous_unmet_load_w`                                         | Previous interval average unmet demand                     |

Optional `Actions` fields: `mode_id`, `pointing`, `processing_enabled`, `downlink_enabled`, and `delete_requests` containing queue IDs and byte counts. Omitted fields preserve current settings; switching mode resets pointing to that mode’s default unless explicitly overridden. Processing/downlink flags are persistent optional overrides; `None` preserves them and a documented reset action returns to mode defaults. Deletion is a one-time action, capped at current queue contents and logged.

Unknown modes/queues, nonfinite values, negative deletion amounts, wrong return types, or script exceptions stop the run with time and a clear error. Existing results remain readable with `failed` status.

### 6.2 Schedule and visual conditional blocks

Exactly one control adapter is active per run. Schedules use nonoverlapping UTC or elapsed-time intervals with requested actions and an explicit fallback. Reject overlapping schedules initially.

Conditional blocks contain an ordered list of conditions and actions, followed by a fallback. First matching condition wins. Support comparisons of documented status fields, `all`, `any`, and `not`; no arbitrary expression evaluation. Mode/dwell-time tests permit hysteresis. Reevaluate at calculation/event boundaries. The visual editor edits this structure rather than introducing a second controller engine. Users can drag condition/action blocks, reorder rules, combine conditions, and select a required fallback. The displayed top-to-bottom order is execution priority. Blocks use typed selectors for status fields, operators, units, mode IDs, and queues; invalid or incomplete blocks are highlighted and prevent starting a run. No loops, recursion, or user-defined functions are supported in the MVP.

The schedule GUI offers start/end time, mode/action, and fallback fields. The script GUI lets users select, inspect, and edit a local Python policy, shows the status/action reference and example, and performs syntax checking before start; runtime errors still fail the run. Switching controller type preserves inactive editor configurations but exactly one is selected for execution. Do not promise lossless conversion between arbitrary Python and visual blocks.

If no controller is supplied, retain the initial mode and its defaults. Protective physical allocation remains active regardless of controller type; entering a named safe mode requires a user rule.

## 7. Calculation order and time semantics

1. Start from committed state at time `t`; compute environment and status.
2. Evaluate the selected controller and validate actions.
3. Apply requested mode/pointing/flags and explicit deletion actions.
4. Choose the next interval boundary: calculation step, schedule boundary, output boundary, known contact/eclipse crossing, or run end.
5. Determine requested component activities and their power/data demand.
6. Allocate physically available bus power by component priority; determine actual powered activities.
7. Compute actual generation, processing, uplink/downlink, queue routing, and storage acceptance for the same interval.
8. Integrate battery energy and commit the energy/data ledgers together.
9. Record events and sampled results; advance time.

Use event splits when queues empty, storage fills, or battery reaches a bound. Recompute allocation for the remaining interval; do not allow a component to operate for the full step after resources run out. Prevent zero-time loops by recording a boundary once and advancing with updated state.

Known geometric crossings are bracketed from propagated geometry and refined to a documented time tolerance. Controller thresholds are checked at interval boundaries; maximum reaction delay is the configured calculation step unless a supported threshold event is explicitly implemented. State this limitation in reports.

Separate calculation step, saved output interval, and GUI refresh rate and optional playback speed. Reject output intervals smaller than the nominal calculation step for the MVP. Always save initial/final state and resource-limit events independently of regular sampling.

## 8. Power accounting

Let `G` be available bus generation, `L` actual served load, `dt_h` interval hours, and efficiencies `eta_c`, `eta_d` in `(0, 1]`.

```text
surplus_w = max(G - L, 0)
deficit_w = max(L - G, 0)
energy_change_wh = eta_c * accepted_charge_bus_w * dt_h
                   - delivered_discharge_bus_w / eta_d * dt_h
```

Charge/discharge bus power is limited by configured limits and available capacity/energy. Generation serves loads first, then charges the battery; remaining generation is curtailed. Battery energy stays between zero and capacity. Report conversion losses, curtailment, requested load, served load, and unmet demand separately.

Power allocation is whole-component, essential first, then explicit priority, then stable component ID. If a full requested activity cannot be powered, try its idle state; otherwise turn it off for that interval. Essential loads can still fail when no energy exists. No invented default load or invisible safe-mode energy is permitted.

User shutdown/recovery thresholds select modes through control rules. The hard zero-energy limit cannot be overridden. Record each affected component and the associated curtailed data activity.

## 9. Data accounting

Canonical units: bytes for stored volume, bytes/s for generation/processing, bits/s for radio. Convert link bits/s to bytes/s explicitly using eight bits per byte. Label CSV units.

Default queues: `raw` and `processed`, sharing one capacity. Default routing is camera → raw → processor → processed → radio. Default processing removes consumed raw input after producing output, with output size equal to consumed input multiplied by the configured size ratio. Retaining raw copies is optional and increases physical occupancy.

Within an interval use a documented operator order: downlink existing eligible data, process available input, accept new producer/uplink data. Newly generated data becomes processable on the next interval; newly processed data becomes downlinkable on the next interval. This is an MVP discretization assumption requiring step-convergence checks.

Do not double-count processing input removal as downlink. Compression changes represented volume; it does not preserve byte count. Keep separate counters for generated raw bytes, processed input/output bytes, downlinked bytes, rejected bytes, and explicitly deleted bytes.

Reject new data that cannot fit, record source/queue/time, and count it as lost. Processing that retains raw data must have room for its output; processing that replaces raw input must account for released space. Never exceed storage capacity temporarily. Deletion policies can free space; physical constraints remain enforced.

The MVP models divisible data volumes, not individual images or packets. It therefore cannot claim that a complete image was delivered. Idle radios transmit nothing; disabled processors consume no input. Multiple producers/processors use stable priority order so allocation is reproducible.

## 10. Equations and user customization

Built-in equations must be visible in the GUI Equations tab, documentation, and report metadata, with units and variable definitions. Their implementation is tested. The MVP displays them as read-only/protected, without an unlock control that suggests editing is available.

MVP customization is via component parameters and control policies. A restricted editable-equation interface, with per-equation protection, is a later milestone. It must define allowed inputs, output units, validation, and failure handling before implementation. Arbitrary policy scripts must not serve as a back door to replacing conservation equations.

## 11. Results and reproducibility

Use one SQLite file per run, append in bounded batches, and keep memory use independent of run duration. Store:

| Table                | Contents                                                                              |
| -------------------- | ------------------------------------------------------------------------------------- |
| `run`                | ID, lifecycle, timestamps, engine version, schema version, completed simulation time  |
| `configuration`      | Original and resolved JSON, defaults, provenance, policy source/hash, model constants |
| `samples`            | Time, mode, position, sunlight, energy, storage, cumulative counters                  |
| `component_samples`  | Optional per-component power/activity at output times                                 |
| `queue_samples`      | Queue occupancy at output times                                                       |
| `events`             | Mode changes, shedding, resource bounds, rejected/deleted data, failures              |
| `interval_summaries` | Min/max states and integrated flows between output samples                            |

State fields are instantaneous at the output timestamp. Flow fields represent the preceding saved interval; cumulative fields cover the run to that timestamp. Preserve minima/maxima and crossing events between samples so coarse output does not hide battery depletion or overflow.

Run inputs are immutable after start. Later project edits affect only a new run. Save policy source, dependency/engine version, assumptions, and a configuration hash. Numerical reproducibility is required within a documented tolerance; bit-identical output across operating systems is not promised.

Required outputs: battery Wh/% plot, generated/served/requested power, queue/total storage plot, cumulative generated/processed/downlinked/lost data, mode timeline, and a constraint/event report. Include energy/data balance residuals and assumptions. CSV export must stream from SQLite. The GUI run browser opens completed and partial runs, exposes their immutable inputs and assumptions, and compares selected runs with aligned elapsed-time or UTC axes. Clearly mark partial/failed runs and unequal time coverage. Parameter sweeps are a later convenience. GUI export buttons and CLI commands call the same export functions.

## 12. Run lifecycle, GUI controls, and CLI

Proposed commands:

```bash
nix develop
everlong-stk gui
everlong-stk gui examples/generic_cubesat/satellite.json
everlong-stk validate examples/generic_cubesat/satellite.json
everlong-stk run examples/generic_cubesat/satellite.json --output runs/example.sqlite
everlong-stk report runs/example.sqlite --output results/
everlong-stk export runs/example.sqlite --output results/samples.csv
everlong-stk compare runs/small.sqlite runs/large.sqlite --output results/comparison/
```

Lifecycle: `created`, `running`, `paused`, `completed`, `cancelled`, `failed`. A pause request is pending until acknowledged at a committed boundary; the UI must not label the run paused before that acknowledgment. Stop requests cancellation and preserves partial results. Restart creates a new run from initial state, preserving the old run.

| State                          | Available controls and editing                                              |
| ------------------------------ | --------------------------------------------------------------------------- |
| No active run / created        | Edit, save, validate, start, browse previous runs                           |
| Running                        | Pause, stop, inspect results; simulation inputs locked                      |
| Pause pending                  | Inspect results, stop; inputs stay locked until acknowledgment              |
| Paused, unchanged inputs       | Resume, restart, stop, edit project draft                                   |
| Paused, changed inputs         | Restart with edited inputs or discard draft changes and resume original run |
| Completed / cancelled / failed | Inspect/export, edit draft, start a new run                                 |

Changing a project while paused never mutates the active run snapshot. Show “Inputs changed — restart required” and disable Resume until edits are discarded. Saving a project does not rewrite old run metadata. Warn before closing with unsaved project edits. Closing during an active run requests cancellation and waits for safe termination; report any failure without falsely marking the run completed. Durable resume after process exit is deferred.

The GUI opens the example satellite on first launch or provides a clear “Open example” action. Field validation identifies the affected tab/component/parameter. Runtime errors show simulated time and a useful message, with technical details available separately. No styling-heavy onboarding is required.

## 13. Illustrative generic CubeSat

All values below are synthetic test inputs, marked `guesstimate`. They are not HYPSO specifications or component recommendations.

- Circular orbit: 550 km altitude, 97.5° inclination, UTC epoch 2027-01-01T00:00:00Z; RAAN/argument/mean anomaly initially 0°.
- One illustrative station: latitude 63.4°, longitude 10.4°, altitude 0 m, minimum elevation 10°, downlink 1 Mbit/s. No implied real station availability.
- Battery 40 Wh, initially 32 Wh, charge/discharge efficiencies 0.95, charge limit 15 W, discharge limit 25 W.
- Storage 1,000,000,000 bytes; initially empty; raw removed after processing.
- A/Idle, B/Imaging, C/Processing, D/Downlink; initial pointing Sun.

| Component                    | A          | B                    | C                                               | D                                     |
| ---------------------------- | ---------- | -------------------- | ----------------------------------------------- | ------------------------------------- |
| Essential platform           | 2 W        | 2 W                  | 2 W                                             | 2 W                                   |
| ADCS                         | 1 W        | 3 W                  | 1 W                                             | 2 W                                   |
| Camera                       | 0.1 W idle | 5 W; 500,000 bytes/s | 0.1 W idle                                      | 0.1 W idle                            |
| Processor                    | 0.2 W idle | 0.2 W idle           | 4 W; 1,000,000 input bytes/s; output ratio 0.25 | 0.2 W idle                            |
| Radio                        | 0.2 W idle | 0.2 W idle           | 0.2 W idle                                      | 6 W; 1 Mbit/s when contact/data exist |
| Solar generation in sunlight | 12 W       | 6 W                  | 12 W                                            | 4 W                                   |

Example policy: A below 20% battery, D when a station is visible and processed data exists, C in eclipse with raw data available, B in sunlight above 40% battery and below 80% storage, otherwise A. The example is expected to expose backlog or energy limitations; it is not designed to hide bottlenecks.

## 14. Validation and acceptance criteria

1. Configuration rejects invalid units, efficiencies, rates, references, schedules, capacities, and nonfinite values. Explicit zero survives default resolution.
2. Renaming a mode leaves policy and schedule references valid.
3. Constant generation/load cases match hand-calculated Wh results including efficiencies, power limits, losses, and curtailment.
4. Battery depletion interrupts affected activities at the bound; no negative energy or unpowered data activity occurs.
5. Processing, raw retention, overflow, deletion, and bit/byte conversion match hand-calculated queue ledgers.
6. Schedules, conditional blocks, and equivalent Python policies produce equivalent actions under the same sampled status inputs.
7. Script failures preserve an identifiable failed run and partial results.
8. Orbit tests cover circular period, coordinate transforms, eclipse geometry, and station elevation. Compare short representative cases with independently generated reference data before claiming engineering fidelity.
9. Production 20-second runs pass a convergence study against finer validation-only steps for minimum charge, energy totals, backlog, and contact duration. Report measured differences rather than a universal accuracy percentage.
10. A synthetic two-year run completes with streamed writes and bounded memory; benchmark runtime, peak memory, database size, and event volume on the user’s M1 Pro before setting performance targets.
11. CSV and plots agree with saved values and retain interval minima/maxima and limit events.
12. GUI and CLI runs from identical resolved inputs/policy produce equivalent saved results within documented numerical tolerance.
13. The GUI remains responsive during representative long runs; pause/stop are acknowledged at safe boundaries, and no worker accesses widgets or shares writer connections.
14. Editing is locked while running, paused edits require restart, and saved run snapshots remain unchanged.
15. Visual block order, typed validation, fallback, and save/reload preserve policy semantics; equivalent blocks and scripts produce equivalent actions.
16. Parameter notes, certainty labels, defaults, explicit zero, mode names, and stable references survive GUI save/reload.
17. GUI plot/export and run comparison agree with CLI outputs; partial runs and missing coverage are visibly identified.
18. Verify GUI launch, scaling, basic keyboard navigation, and file dialogs on macOS and Linux, and ordinary Python installation on Windows before claiming cross-platform GUI support.
19. A new contributor can follow the simulation loop, policy contract, and accounting equations from the README without framework-specific knowledge.

## 15. Implementation milestones

1. **Schema and accounting:** data classes, resolved configuration, hand-calculated power/data tests, example satellite.
2. **Environment and control:** orbital environment, station access, schedule and conditional-rule representation, Python policy contract.
3. **Integrated runner:** event splitting, physical allocation, SQLite, immutable snapshots, shared lifecycle functions, CLI.
4. **Basic desktop GUI:** left/right workspace, parameter and mode editors, schedule/script control, worker, start/pause/stop/restart, embedded plots, events, project save/load.
5. **Visual control and comparisons:** Scratch-inspired ordered block editor, typed validation, run browser, comparisons, shared exports, read-only equations.
6. **Engineering and scale validation:** convergence studies, two-year benchmark, responsiveness, documentation, OS portability checks.

The first usable GUI may precede the visual editor, but both belong to the specification. Later work includes restricted editable equations, parameter sweeps, uncertainty scenarios, richer orbit validation, geometry-based solar generation, optional map/playback, and requirement/verification traceability.

## 16. Decisions to verify during implementation

These do not block the first implementation: orbit dependency and long-duration approximation; two-year performance; acceptable 20-second numerical errors; final CSV column names; PySide6 packaging; worker-thread responsiveness; plot query/aggregation limits. Record decisions in short plain-language notes. Changes to accounting, controller timing, or configuration semantics require a schema/version update and corresponding validation. GUI presentation changes alone do not require a configuration schema change.
