# EverlongSTK — shared models and project configuration

Task 001 prepares the configuration layer for the local satellite budget simulator.
The existing GUI scaffold is unchanged; physics and controller execution are future work.

## Development

From this directory (`everlongstk/` inside the Git checkout):

```sh
nix develop
python -m pytest
ruff check .
python -m everlong_stk --help
```

The existing flake pins Nixpkgs 25.05 and provides Python 3.12, pytest and Ruff.
Without Nix, use Python 3.11+ in an isolated virtual environment with pytest and
Ruff installed. Tests configure `src` on the import path; for CLI/API use set
`PYTHONPATH=src`. Do not mix a separate pip Qt installation into Nix Python.

## Project API

```python
from pathlib import Path
from everlong_stk.configuration import (
    load_project, validate_project, resolve_project, save_project,
    export_component_table,
)

config = load_project(Path("examples/generic_cubesat.json"))
assert validate_project(config) == ()
resolved = resolve_project(config)
print(resolved.components[0].mode_values["a"].nominal_load_w)
save_project(Path("my_cubesat.json"), config)
export_component_table(config, Path("components.csv"))
```

`load_project` rejects invalid JSON/configuration. `validate_project` returns the
first path-specific `ValidationIssue` (or an empty tuple); dictionaries are also
accepted for incomplete editor drafts. `resolve_project` returns a fresh typed
configuration with defaults and nominal bus power, without mutating its input.
`save_project` validates before writing and preserves original input/provenance
when unchanged. Typed edits using `dataclasses.replace` update current values
without overwriting unrelated omissions or metadata.

The older `load_configuration`, `validate_configuration`, `save_configuration`
and `resolved_to_dict` entry points remain available. The latter exports an
annotated run/report snapshot, **not** a reloadable project document. Use the
project API when editing typed objects.

## Configuration conventions

The complete example uses integer `schema_version: 1`, a 550 km / 97.5 degree
orbit, 5 V bus, 40 Wh battery, 1,000,000,000 byte storage, raw/processed queues,
and Idle, Capturing data, Transmit/receive and Survival states. All engineering
values are synthetic estimates, not hardware specifications or simulated results.

Numerical engineering inputs use `{value, unit, certainty, note, source,
lower_bound, upper_bound, is_default}` parameter metadata. Canonical units are
strict: `kg`, `m`, `deg`, `s`, `V`, `A`, `W`, `Wh`, `byte`, `byte/s`, `bit/s`,
`%`, and dimensionless `1`. No implicit unit conversion occurs. Certainty is one
of `guesstimate`, `calculated_estimate`, `specified`, `tested`.

Every component requires a signed `current_a` for every state under `mode_values`.
Every producer also requires `data_generation_bytes_per_s` for every state.
Explicit zero is preserved; missing required values fail validation. Negative
current requires an enabled generator. Nominal load/generation are separately
resolved from voltage × current; actual power allocation is outside this task.
Exactly one physical battery and one physical storage device are required.

Optional advanced idle power, processing/link rates, queue routing and control
fields retain the starter's documented defaults, recorded in `defaults_applied`
and parameter `is_default` flags. Conditional activity has explicit idle-power
inputs; this foundation makes no claim of implemented power accounting.

CSV contains one row per component with mass, type, relevance/capacity/link
fields and per-state current/data/radio rates. Headers include stable state IDs
and units. State labels are separate cell values, so renaming preserves headers.

See [Task 001 contract notes](docs/tasks/001_contract_notes.md) for the proposed
schema freeze, compatibility details, validation report and unresolved questions.
