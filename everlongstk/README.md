# EverlongSTK — Development Task 001

Implementation of the **configuration and shared-model foundation** from
EverlongSTK specification v0.2. No simulation engine, policy executor, or GUI
is included in this milestone.

## Development

```sh
nix develop
python -m pytest
ruff check .
```

The pinned `flake.lock` selects NixOS/nixpkgs 25.05; `flake.nix` provides Python
3.12, pytest, Ruff, and `PYTHONPATH=src`. Nix is required to verify the flake
on your own machine; this supplied environment did not have Nix installed.

Without Nix, use Python 3.11+ and pytest, set `PYTHONPATH=src` (or install the
package with `pip install -e .`), and run `python -m pytest`.

## API

```python
from everlong_stk.configuration import (
    load_configuration, save_configuration, validate_configuration,
    resolved_to_dict,
)

config = load_configuration("examples/generic_cubesat.json")
print(config.orbit.semi_major_axis_m.value)
print(config.defaults_applied)
print(resolved_to_dict(config)["components"][0])
save_configuration(config, "my_cubesat.json")
```

- `validate_configuration(raw_dict)` is the authoritative model validator.
  It returns typed, frozen data classes and raises `ConfigurationError` with
  a path to the invalid input. It does not mutate the caller's dictionary.
- `load_configuration(path)` validates UTF-8 JSON, including duplicate-key
  rejection. `save_configuration(config, path)` stores the original input
  values **without injecting defaults or losing metadata**.
- `resolved_to_dict(config)` returns the fully resolved model, including
  `is_default` on parameters and `defaults_applied` path names. This is a
  run/report snapshot, not an input project file. The optional
  `save_configuration(config, path, resolved=True)` writes such a snapshot.
- IDs (not user-editable labels) are used for all references. Renaming a mode
  label therefore does not affect controllers or component mode maps.

## Configuration conventions

The example covers modes A–D, compound component capabilities, a circular
550 km orbit, one synthetic station, an illustrative battery, one shared
storage device with raw/processed queues, and typed conditional-control data.
All of its numerical engineering inputs are synthetic **guesstimates**, not
specifications or pass predictions.

Every explicit numeric engineering input is a metadata object:

```json
{
  "value": 8.0,
  "unit": "W",
  "certainty": "specified",
  "note": "Illustrative value",
  "source": null,
  "lower_bound": null,
  "upper_bound": null
}
```

Canonical units are strict (no automatic conversion): `kg`, `m`, `deg`, `s`,
`W`, `Wh`, `A`, `byte`, `byte/s`, `bit/s`, `%`, and dimensionless `1`.
Allowed certainty values are `guesstimate`, `calculated_estimate`,
`specified`, and `tested`. Bounds, if present, must include the nominal value.
Nonfinite values, booleans in numerical fields, negative capacities/rates,
unknown fields, malformed timestamps, and broken references are rejected.

Per-mode **power** values are `idle_power_w` and `active_power_w`; optional
`idle_current_a` and `active_current_a` preserve user-provided current draws.
Current draws are not automatically converted to watts: that would require an
explicitly defined voltage/model, which is outside this milestone. Power in
watts remains authoritative for the proposed future resource accounting.
Modes also contain `active`, `generation_w`, `data_generation_bytes_per_s`,
`processing_input_bytes_per_s`, `downlink_bps`, and `uplink_bps`. Missing
per-mode values default independently to `false` or numerical zero and are
recorded in `defaults_applied`; explicit zero remains nondefault. Disabled
loads and work-conditioned power are calculation rules for the future engine,
not computed here.

Defaults are 20 s calculation steps and 60 s output samples (or the calculation
step if greater than 60 s), initial empty data queues `raw` and `processed`
when omitted, route names `raw`/`processed`, `false` for raw retention,
`sun` pointing, and `none` control when absent. Every missing routing value
is recorded. `defaults.initial_mode_id`, orbit geometry, project identifiers,
component mass and capabilities, and required physical capacities are mandatory.
The circular convenience orbit uses 6,378,137 m (WGS-84 equatorial radius)
to resolve semi-major axis. The advanced form takes `semi_major_axis_m` and
`eccentricity`; both forms resolve the remaining orbital elements in
`ECI_J2000`. Propagator names are `kepler` and `kepler_j2`.

Supported configuration control types are `none`, `python`, `schedule`, and
`blocks`. Schedule intervals cannot overlap. Condition trees support
`all`/`any`/`not` and typed comparisons; any mode or queue referenced by a
rule must exist. Runtime execution and validation of Python scripts is a
subsequent task. An empty station availability list means no scheduled
restriction in this model, not confirmation of real-world contact.
