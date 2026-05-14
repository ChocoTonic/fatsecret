"""Legacy entry point — kept for back-compat with users who scripted
`python examples/cli_example.py`. The actual example lives in main.py.
"""

from .main import main  # noqa: F401  (re-export for callers that import this name)

if __name__ == "__main__":
    import sys

    from .main import main as _main

    sys.exit(_main())
