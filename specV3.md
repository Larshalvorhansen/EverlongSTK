# EverlongSTK — Minimal Implementation Specification

Version 0.3

## 1. Purpose

Build a native desktop application for rapid prototyping of satellite missions, focusing on:

- Power generation, consumption and battery state
- Data generation, compression, storage and downlink
- Orbital position, sunlight and ground-station visibility
- Satellite operating modes and control logic

Target users are satellite systems engineers and small satellite development teams.

Prioritize **correctness, modularity, simplicity and usability** over visual polish or high-fidelity physics.

## 2. Technology

- Python 3.12+
- Nix flake (`nix run` must launch the application)
- PySide6 for the native GUI
- NumPy for numerical calculations
- PyQtGraph for plots
- SQLite for persistent projects and results
- JSON for configuration import/export
- Model-View-Controller (MVC) architecture

No browser interface or web server.

Keep the simulation engine independent of the GUI.

## 3. GUI

Use the three attached reference screenshots as design inspiration. Functional similarity is more important than pixel-perfect reproduction.

### Top bar

Simulation controls:

- Run/play
- Pause
- Step forward
- Step backward
- Stop
- Reset
- Playback speed
- Current simulation time

Simulation results are calculated before playback. Playback navigates through saved timestep results.

### Left panel — Configuration

Three tabs:

1. **Components:** Add, edit and remove satellite components. Configure power consumption per mode, solar generation, battery and storage.
2. **Orbit:** Configure orbital elements and ground stations.
3. **Controller & Settings:** Edit the mode controller and simulation duration, timestep and initial conditions.

### Right panel — Results

Two selectable views:

**1. Satellite & Position**

- 2D schematic of satellite orientation and pointing
- Current mode, battery level, consumption, generation, storage and downlink rate
- World map showing satellite location, ground track and ground stations

**2. Plots**

- Power generation, consumption, net consumption and battery energy over time
- Data generated, downlinked, occupied storage and remaining storage over time

All views must synchronize to the selected simulation timestep.

## 4. Simulation Model

Implement deterministic, fixed-timestep simulation.

At each timestep:

1. Calculate orbit position using two-body Keplerian propagation.
2. Calculate Earth rotation, sunlight/eclipse and ground-station visibility.
3. Evaluate the selected mode controller.
4. Determine satellite pointing and solar generation.
5. Calculate component power consumption and battery changes.
6. Calculate data generation, effective compression and downlink.
7. Apply battery, power and storage constraints.
8. Record the complete simulation state.

Use SI units internally, with convenient units in the GUI.

### Components

Each component has:

- Name
- Optional mass
- Power consumption in watts for each operating mode
- Optional data generation or downlink parameters

Missing mode-specific power values inherit a configured default.

Solar generation depends on sunlight, pointing and effective panel area.

### Battery

Model:

- Energy capacity (Wh)
- Initial energy
- Charge/discharge efficiency
- Maximum charge/discharge power
- Energy limits

### Storage

Use one aggregate storage counter, not separate raw and processed queues.

Model generated data, effective compression, transmitted data, dropped data and remaining storage. Enforce capacity limits and conservation of data.

### Orbit

Support initially:

- Circular and elliptical Keplerian orbits
- Altitude or semimajor axis
- Inclination
- RAAN
- Argument of periapsis
- Initial anomaly
- UTC epoch
- Ground-station latitude, longitude, altitude and minimum elevation

Use a simple cylindrical Earth-shadow model initially. Document approximations.

## 5. Mode Controller

Support two interchangeable controller implementations.

### A. Visual Flowchart

Editable node-based graph with:

- Operating-mode nodes
- Conditional nodes
- Connections/transitions
- Configurable transition priority
- Validation of invalid states and connections

### B. Custom Python Script

Allow users to supply a Python file implementing a predefined function:

```python
def decide(state, config):
    return {
        "mode": "Imaging",
        "pointing": "Nadir"
    }
```

Inputs must expose documented, typed, read-only values including:

- Time and satellite position
- Battery state
- Storage occupancy
- Sunlight/eclipse
- Ground-station visibility
- Previous operating mode
- Mission configuration

Outputs specify:

- Operating mode
- Pointing target

The visual controller and Python controller must conform to the **same interface**.

Validate outputs before using them. Execute custom scripts in a separate process with timeouts. Treat scripts as trusted user code, not sandboxed code.

## 6. Example Mission

Include a working generic CubeSat example with synthetic test values:

- Circular orbit, altitude 550 km, inclination 97.5°
- Epoch: 2027-01-01 00:00 UTC
- Battery: 40 Wh, initially 32 Wh
- Storage: 1 GB, initially empty
- Solar generation: up to 12 W
- Ground station: 63.4° N, 10.4° E, minimum elevation 10°
- Downlink: 1 Mbit/s
- Modes: Idle, Imaging, Processing, Downlink

Example control policy:

1. Battery below 20% → Idle
2. Station visible and stored data available → Downlink
3. Eclipse and stored data available → Processing
4. Sunlight, battery above 40%, storage below 80% → Imaging
5. Otherwise → Idle

Processing uses an effective data-rate/compression approximation rather than a separate raw-data queue.

Label all example values as illustrative estimates, not real spacecraft specifications.

## 7. Project Structure

```text
everlongstk/
├── flake.nix
├── pyproject.toml
├── src/everlongstk/
│   ├── model/
│   ├── control/
│   ├── view/
│   ├── controller/
│   ├── persistence/
│   └── main.py
├── examples/
└── tests/
```

Keep modules small and responsibilities explicit. Avoid unnecessary frameworks and abstractions.

## 8. Implementation Order

1. Build and test the simulation engine without a GUI.
2. Implement the shared controller interface and custom Python controller.
3. Build the native GUI and configuration editors.
4. Add playback, synchronized plots, ground track and satellite schematic.
5. Implement the editable visual flowchart controller.
6. Add SQLite persistence, imports/exports and integration tests.

Complete each stage before unnecessarily expanding its scope.

## 9. Acceptance Criteria

The project is complete when:

- `nix run` launches the native application.
- The example CubeSat mission loads automatically or from an example selector.
- Users can edit components, orbit, ground stations and simulation settings.
- Users can create a visual control flowchart or supply a Python controller.
- A complete 90-minute simulation can be calculated.
- Users can play, pause, step backward/forward and reset.
- Satellite position, status and plots update synchronously.
- Battery and storage constraints are enforced correctly.
- Configurations and results can be saved and loaded.
- Automated tests validate orbital propagation, ground contact, battery, data accounting, controller behavior and deterministic replay.

## 10. Instructions to the Implementing LLM

**Implement the application, not merely a mockup.**

- Prefer the simplest reliable solution.
- Make reasonable engineering decisions without requesting approval for minor details.
- Do not introduce unnecessary features or dependencies.
- Keep numerical calculations separate from GUI code.
- Write tests for physical calculations and state transitions.
- Document assumptions and approximations.
- Do not silently invent physical behavior.
- Do not claim a feature works unless it has been implemented and tested.
- If something is incomplete, clearly identify it.
- Prioritize a runnable end-to-end application over isolated polished components.

**Final deliverable:** Complete source code, working Nix environment, example mission, tests and a concise README with launch instructions.
