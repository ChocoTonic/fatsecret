"""Dependency-light entry point for the optional member-web facade."""


def main() -> None:
    try:
        from .facade import main as run
    except ImportError as error:  # pragma: no cover - built distribution behavior
        raise SystemExit(
            'The HTTP facade requires optional dependencies; install "fatsecret[facade]".'
        ) from error
    run()


__all__ = ["main"]
