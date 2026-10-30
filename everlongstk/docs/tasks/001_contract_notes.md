# Task 001 contract proposal and validation

This implementation is submitted for architectural review. It reuses the starter's
standard-library parser, capability models, orbit resolution and control-data
validation. It does not execute transitions, allocate resources, propagate orbits,
write SQLite, or change the GUI scaffold.

## Choices implemented for this review

- The complete example freezes **integer schema version 1**, as proposed by module
  contract section 8. Starter string version `"0.2"` is rejected rather than silently
  migrated: it permitted missing per-state values and authoritative W fields, so
  treating it as compatible would invent signed currents and bus voltage.
- Top-level `states` replaces `modes`. Existing engineering names `project.title`,
  state `label`, simulation `duration_s`/`calculation_step_s`/`output_interval_s`,
  `mode_values`, `initial_mode_id` and controller `mode_id` remain explicit in this
  complete schema. The section 8 JSON was only a partial illustration. `states`
  and `name` properties expose configuration states and editable state names;
  `ProjectConfig`, `ResolvedProjectConfig`, `StateDefinition`, `ComponentConfig`,
  `OrbitConfig` and `GroundStationConfig` alias the existing concrete model types.
  Load returns already resolved typed data; re-resolution is nonmutating.
- Signed current is authoritative. Input W-generation/active-power fields are
  rejected; nominal generation/load W are derived separately. Enabled generator
  capability authorizes negative current. Original current/voltage metadata remains
  available. Advanced `idle_power_w` remains a separate nonnegative input (default
  zero, marked `is_default`); active/idle selection belongs to future allocation.
  This resolves the executable input convention, not the physics-parity gate.
- Exactly one battery and one positive-capacity physical storage owner are required.
  Stable IDs remain scoped to their collections. Component `type` is a required
  descriptive string; capability flags, rather than that label, determine behavior.
- Transition IDs, endpoints, structured conditions, nonnegative integer priorities
  and optional nonnegative `minimum_dwell_seconds` are validated and round-trip.
  Declaration order is retained, including priority ties. No state evaluator exists.
- Runtime snapshots/events use datetime fields; configuration timestamps retain
  validated explicit UTC ISO-8601 strings at the JSON boundary. Snapshots and all
  power/data ledger mappings are defensively copied and exposed read-only.
  Power ledgers use integrated Wh, data ledgers use bytes; processing input/output
  and ending queue occupancy are separate. No conservation calculation is performed.
- CSV uses `state[stable_id].current_A` and corresponding byte/s and bit/s headers.
  Labels are cells, never identifiers. Inapplicable capability fields are blank,
  explicit zero is `0`, and CSV quoting handles commas, quotes and newlines.
- Validation is fail-fast with one structured issue per call; it never fills missing
  required values to collect further errors. Save validates before touching a file.
  Original JSON is retained for unchanged round trips; typed edits merge only changed
  input fields. Resolved report snapshots are deliberately not project input JSON.
- Restored the missing package `__version__` export used by the existing CLI; no
  command or GUI behavior was added.

## Still unresolved for integration review

1. Approve the complete schema and compatibility aliases above before other modules
   rely on them. A separate migration/import tool is needed for starter or mockup
   JSON; no automatic migration is provided here.
2. Confirm long-term idle-current versus idle-power editing and defaults, and how a
   compound load/generator represents simultaneous consumption and generation. One
   signed current represents a net nominal input, not two independently measured flows.
3. Define precedence between diagram transitions and a selected schedule/block/Python
   controller, transition priority direction, hysteresis, dwell timing and fallback
   semantics in the control task. These inputs are only data here; the example has
   `control.type: none` and an illustrative transition. No execution policy is implied.
4. Agree future numerical tolerances, event refinement and output policy/constants
   with the physics/coordinator tasks. The new ledgers are typed interval data;
   they do not establish numerical correctness, scheduling or result persistence.
5. Nix/Qt and interactive platform verification remain separate work. This task does
   not change the existing Nix package set or claim GUI support.

## Verification

Run from `everlongstk/` in the checkout, with Python 3.12.14 and an isolated venv:

```sh
/workspace/.venvs/everlongstk/bin/python -m pytest -q
/workspace/.venvs/everlongstk/bin/ruff check .
PYTHONPATH=src /workspace/.venvs/everlongstk/bin/python -m everlong_stk --help
```

Pytest and Ruff exercise configuration validation/serialization, stable identity,
explicit zero/missing values, signed-current arithmetic, capacity/efficiency limits,
control-data validation, CSV values/quoting/renames, typed edits/provenance and immutable
runtime models. Test totals and current results are recorded in the pull request.

`nix --version` fails with command not found, so `nix develop`/flake evaluation could
not run. The tracked `flake.nix` and `flake.lock` are unchanged. Qt/GUI checks were not
run because GUI implementation is outside Task 001.
