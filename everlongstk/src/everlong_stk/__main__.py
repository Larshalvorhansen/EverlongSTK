"""Allow ``python -m everlong_stk`` without installing console scripts."""

from everlong_stk.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
