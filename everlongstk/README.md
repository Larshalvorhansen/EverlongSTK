# EverlongSTK

A proposed local satellite power/data budget simulator built with Python and PySide6.

**Current repository status: architectural starter only.** The real simulation engine and the faithful GUI have not been implemented. Running the `gui` command shows a simple three-tab Qt shell; this is deliberately **not** a replacement for the detailed HTML mockup.

## Design references

- **Implementation contract:** `docs/module_contracts_v0.1.md`
- **Engineering baseline:** `docs/reference/specV2.md` (v0.2)
- **GUI visual specification:** `docs/reference/everlongstk_mockup.html` — open in a browser to inspect the target layout and controls.

The three main Qt tabs must match the HTML reference: **Configuration**, **Simulation**, and **Results**. The final interface should preserve the three Configuration sections, orbital inputs, interactive state-machine editor, components with per-state current/data generation, Earth map, live battery and storage statistics, and exports.

## Nix development environment

Nix with flakes enabled is required for the primary supported development workflow:

```bash
git init
git add .
nix flake lock    # creates flake.lock from actual dependency revisions
git add flake.lock
nix develop
python -m everlong_stk --help
python -m everlong_stk check-env
python -m pytest
ruff check .
python -m everlong_stk gui
```

**Commit `flake.lock`**. It is intentionally not included in this starter because the generation environment does not have Nix; do not manufacture a lockfile manually. Nixpkgs is initially set to `nixos-26.05` and supports the declared `aarch64-darwin`, `x86_64-linux`, and `aarch64-linux` devShell outputs subject to target verification.

The shell uses the Python/PySide6/NumPy/Matplotlib/PyQtGraph packages from the **same Nixpkgs package set** and keeps `src/` on `PYTHONPATH`. Do not pip-install a second Qt into the Nix Python environment.

Qt WebEngine is **optional at bootstrap**: its current availability and graphical behavior must be verified on the actual target systems before it can be made a required dependency. The specification requires an offline map fallback.

## Without Nix

Python 3.13 or later (where available) and a working system-specific Qt installation:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
python -m everlong_stk gui
```

This is an installation alternative, not a reproducibility substitute for the committed flake lock.

## Planned development

1. Freeze shared models and JSON schema with numerical fixtures.
2. Implement orbit, control, power, data, and results as independently tested modules.
3. Wire a minimal end-to-end headless simulation early; continuously replace stubs with real modules.
4. Build the faithful Qt UI in parallel using fake snapshots, then connect it to the engine.
5. Validate physical accounting, long runs, plotting, reproducibility, and macOS/Linux packaging.

See the detailed handoff table and module acceptance tests in `docs/module_contracts_v0.1.md`.
