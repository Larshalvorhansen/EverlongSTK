"""Small bootstrap CLI. Physics and result commands are not implemented yet."""

import argparse

from everlong_stk import __version__


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="everlong-stk",
        description="EverlongSTK — satellite budget simulator (development scaffold)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Launch the minimal three-tab PySide6 shell")
    commands.add_parser("check-env", help="Print installed Qt/Python support")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    if args.command == "gui":
        # Keep Qt entirely out of core/CLI import paths until requested.
        from everlong_stk.gui.app import run_gui

        return run_gui()
    if args.command == "check-env":
        import sys

        print(f"Python: {sys.version.split()[0]}")
        try:
            import PySide6

            print(f"PySide6: {PySide6.__version__}")
            try:
                from PySide6.QtWebEngineWidgets import QWebEngineView  # noqa: F401
            except ImportError:
                print("Qt WebEngine: unavailable (map fallback required)")
            else:
                print("Qt WebEngine: importable (display smoke test still required)")
        except ImportError:
            print("PySide6: unavailable")
            return 1
        return 0
    create_parser().print_help()
    return 0
