# EverlongSTK — contributor instructions for Codex

EverlongSTK is a local satellite power/data budget simulator with a native PySide6 GUI and a headless Python CLI. This is an engineering simulation tool, not a web service. Optimize for correctness, clarity, reproducibility, and human maintainability.

## Relevant references

- `docs/module_contracts_v0.1.md`: module boundaries, public APIs, canonical units, lifecycle, and acceptance criteria. Consult the relevant sections before changing a contract.
- `docs/reference/specV2.md`: original engineering requirements, timing, power/data accounting, orbital assumptions, and physical constraints.
- `docs/reference/everlongstk_mockup.html`: authoritative visual and interaction reference for the three PySide6 tabs. Its animated numbers are illustrative, **not valid reference physics**. Consult it for GUI tasks.
- `README.md`: repository setup and current implementation status.

Where references disagree, follow the precedence and unresolved-decision policy in section 0 and section 15 of the module contract. Do not silently decide disputed physical semantics.

## Architecture

- Use a single Python package under `src/everlong_stk/`. Do not introduce microservices, web APIs, plugin frameworks, dependency-injection systems, or speculative abstractions.
- Keep `models.py` free of dependencies on other project modules. Share small, typed data classes and explicit units.
- Core scientific modules (`orbit.py`, `control.py`, `power.py`, `data.py`, `simulation.py`) must not import Qt, GUI code, SQLite, or plotting libraries.
- Keep JSON parsing/validation in `configuration.py`; SQLite access in `results.py`; the GUI should consume public APIs and committed results instead of independently simulating physics.
- Use stable IDs for states, components, and stations. Do not use editable names as identifiers.
- Respect physical limits: battery energy and storage occupancy cannot become negative or exceed capacity; unpowered components cannot generate/transmit data; downlinked bytes are removed from onboard queues only after successful transmission.
- Signed per-state currents in the UI are an input convention (negative for qualified generators). Core power allocation uses W and Wh with an explicit bus voltage. Data uses bytes, bytes/s and bits/s as specified.
- Keep source code readable: descriptive names, type hints, small functions, concise docstrings when behavior or units are nonobvious, and no framework-heavy patterns.

## Working agreement

- Work on the named task only; avoid unrelated refactors or complete rewrites.
- Before changing shared public interfaces, the JSON schema, calculation order, physical assumptions, or unit conventions, identify the conflict and propose an explicit change for review. Update docs and tests with any approved change.
- Prefer hand-calculated and independently checked test cases to self-referential assertions.
- Tests must cover nominal cases, zero versus missing values, invalid inputs, limit events, and serialization where applicable.
- Do not claim that a test, GUI smoke test, or Nix build passed unless it was actually run. If the environment lacks Nix/Qt or network access, say so and report which checks were possible.
- Keep dependencies minimal and do not `pip install` a separate Qt stack into the Nix-managed Python environment.
- Do not hand-edit or fabricate `flake.lock`; generate it with `nix flake lock` when Nix is available and commit it.
- Produce a concise handoff with changed files, tests run/results, deviations, and unresolved questions. Do not commit generated simulations or large binaries unless explicitly requested.

## Development checks

Within the Nix shell, when available:

```sh
nix develop
python -m pytest
ruff check .
python -m everlong_stk --help
```

For GUI tasks, separately smoke-test on an actual GUI-enabled environment; headless tests alone are not sufficient. Use topic branches/PRs when supported; do not push directly to `main` without approval.
