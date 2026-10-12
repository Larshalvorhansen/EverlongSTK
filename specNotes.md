# EverlongSTK Specification

## Satellite Budget Simulator

## 1. Purpose

Simple STK for rapid prototyping of satellite design in terms of:

- Power budget
- Link budget / data storage capacity

**Primary users:**

- System engineers
- Small satellite teams planning/drafting satellite missions

## 2. Product Boundaries

- Initially launched from a Nix flake with a native GUI
- No browser interface

## 3. Software Architecture

Model-View-Controller (MVC) architecture.

### MVC Architecture: Layer Responsibilities

| Layer          | Responsibility                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Model**      | Config; components; orbit specifics; power and data extrapolation; timestep settings; SQLite storage; control policy (the rules for deciding what happens for each timestep)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **View**       | Data entry for component values on the LHS; satellite position according to orbit on the bottom RHS; on the top RHS: close-up view of the satellite orientation (nadir, solar maximization, other) along with battery power status, charging level, consumption level, mode at the moment, down/uplink speed, data storage status. One can toggle between data entry view on the LHS and plots (battery power over time in the same plot as solar generation and power consumption and a net consumption (consumption − generation)); also a similar plot of data generation (storage capacity remaining, data generated, data downlinked to earth (storage capacity = total data generated − total data downlinked to earth)) |
| **Controller** | GUI button handlers; interface between View and Model                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

### 3.1 GUI Workspace

**LHS:** Inputs toggle between 1, 2, and 3:

1. Data entry/view of components
2. Specify type of orbit
3. Specify ground station positions, mode controller flowchart edit, edit simulation settings (timestep interval)

**RHS:** Toggle between 1+2 and 3:

1. Satellite orientation and status view
2. Satellite position view
3. Plots:
   - Battery power over time in the same plot as solar generation, power consumption, and net consumption (consumption − generation)
   - Data generation (storage capacity remaining, data generated, data downlinked to earth, where storage capacity = total data generated − total data downlinked to earth)

**Top bar:** Simulation buttons: start, step forward, backward, pause, stop, and reset buttons (represented by the commonly used symbols; button name on hover)

## 4. Project Configuration

### 4.1 Components

User specifies the average current draw for all components in each mode. If only one mode has a value, the other modes assume the value of the one given.

Solar panel is also just a component which has a negative current draw if it is on the sunny side of Earth and an attenuation proportional to the effective area.

Each component also has an optional mass value.

The antenna has some common downlink specs (bandwidth, baud rate, dB gain), but up and downlink speeds are the most important here (Mb/s).

## 5. Orbit and Environment

User specifies type of orbit, starting position, angle of incidence, and altitude.

## 6. Generic CubeSat Example

All values below are synthetic test inputs, marked `guesstimate`. They are not HYPSO specifications or component recommendations.

- **Circular orbit:** 550 km altitude, 97.5° inclination, UTC epoch 2027-01-01T00:00:00Z; RAAN/argument/mean anomaly initially 0°.
- **One illustrative station:** latitude 63.4°, longitude 10.4°, altitude 0 m, minimum elevation 10°, downlink 1 Mbit/s. No implied real station availability.
- **Battery:** 40 Wh, initially 32 Wh, charge/discharge efficiencies 0.95, charge limit 15 W, discharge limit 25 W.
- **Storage:** 1,000,000,000 bytes; initially empty; raw removed after processing.
- **Modes:** A/Idle, B/Imaging, C/Processing, D/Downlink; initial pointing Sun.

| Component                    | A          | B                    | C                                               | D                                     |
| ---------------------------- | ---------- | -------------------- | ----------------------------------------------- | ------------------------------------- |
| Essential platform           | 2 W        | 2 W                  | 2 W                                             | 2 W                                   |
| ADCS                         | 1 W        | 3 W                  | 1 W                                             | 2 W                                   |
| Camera                       | 0.1 W idle | 5 W; 500,000 bytes/s | 0.1 W idle                                      | 0.1 W idle                            |
| Processor                    | 0.2 W idle | 0.2 W idle           | 4 W; 1,000,000 input bytes/s; output ratio 0.25 | 0.2 W idle                            |
| Radio                        | 0.2 W idle | 0.2 W idle           | 0.2 W idle                                      | 6 W; 1 Mbit/s when contact/data exist |
| Solar generation in sunlight | 12 W       | 6 W                  | 12 W                                            | 4 W                                   |

**Example policy:** A below 20% battery; D when a station is visible and processed data exists; C in eclipse with raw data available; B in sunlight above 40% battery and below 80% storage; otherwise A. The example is expected to expose backlog or energy limitations; it is not designed to hide bottlenecks.
