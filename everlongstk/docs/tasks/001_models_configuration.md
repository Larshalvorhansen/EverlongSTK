# Task 001 — Implement shared models and project configuration

Status: Ready for first bounded implementation task.  This is the first module contract freeze, not an implementation of the GUI or physics.

## Read first

- `AGENTS.md`
- `docs/module_contracts_v0.1.md`, especially sections 0–5, 8, 10–12 and 15
- `docs/reference/specV2.md`, especially configuration and parameter sections
- Existing `src/everlong_stk/`, `tests/`, `pyproject.toml`, `flake.nix`, `README.md`

Review the existing repository state before editing. If this repository does not yet contain those files, report what is missing and scaffold only the missing foundation without overwriting existing code.

## Scope

Implement the shared configuration/data-model layer, keeping the public API aligned with the module contract:

- `src/everlong_stk/models.py`: typed data structures for project configuration, states, transitions, components, ground stations, simulation/orbit parameters, runtime snapshots, actions, ledgers/events, and validation issues, to the level required for stable shared contracts. Keep names, canonical units, and immutable runtime snapshots explicit.
- `src/everlong_stk/configuration.py`: `load_project`, `save_project`, `validate_project`, `resolve_project`, and `export_component_table`; add private helpers as needed.
- `examples/generic_cubesat.json`: a complete, synthetic, validated four-state example (Idle, Capturing data, Transmit/receive, Survival) with 550 km / 97.5 degree inclination example orbit, 40 Wh battery, 1,000,000,000 byte storage, representative components, explicit per-state signed currents, and per-state data-generation rates. Mark illustrative values as estimates, not real hardware specifications. Adapt other sample fields to the approved contracts.
- `tests/test_configuration.py` and appropriately scoped model tests.
- A short note documenting any choices required to make proposed contracts executable, distinguishing resolved from unresolved decisions.

## Acceptance tests

1. The example configuration loads, validates, resolves defaults, and saves/loads without changing stable IDs, explicit zero values, required per-state values, or provenance.
2. Missing values are not silently replaced with zero; added states require values for each component wherever required.
3. Bad units, non-finite quantities, invalid references, duplicate IDs, invalid capacities, negative data rates, impossible battery efficiencies, and missing per-state current/data rates generate useful validation errors.
4. A signed negative current is accepted only for components with generator capability and is correctly translated to nominal W using the configured bus voltage; non-generators cannot consume negative power.
5. Exactly one physical battery and one physical storage device are supported for the initial release, with appropriate configuration validation.
6. Component CSV output has component row number, stable ID, name, type, mass, battery/data relevance and capacities, ground link details, and columns for each state's signed current and data-generation rate. Dynamic state labels should not destroy identity.
7. Tests pass; Ruff passes; record verification commands and any Nix/environment limitations.

## Explicitly out of scope

- Orbit propagation or Earth map.
- State-machine evaluation or Python generation.
- Power/battery or data storage simulation logic.
- SQLite run persistence.
- PySide6 implementation or redesign of the HTML mockup.
- Unrequested rewrite of the existing starter project.

Do not change physics semantics or interface contracts just to satisfy a convenient implementation. Flag unresolved ambiguities for architectural review.

## Expected deliverable

A focused feature branch or pull request with code, example JSON, tests, any approved contract documentation updates, a brief test report, and a note listing unresolved design questions.
