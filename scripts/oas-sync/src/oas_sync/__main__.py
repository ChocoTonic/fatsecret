"""CLI entrypoint."""

from __future__ import annotations

import logging

import typer

from .discover import discover, group_by_category
from .emit import emit_inventory, emit_openapi, emit_raw_yaml
from .http import fetch
from .models import MethodRef
from .parse import parse_page

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@app.command()
def sync(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    force: bool = typer.Option(False, "--force", help="Bypass cache for all fetches"),
) -> None:
    """Full pipeline: discover → fetch → parse → emit."""
    _configure_logging(verbose)
    refs = discover()
    emit_inventory(refs)

    specs_by_category: dict[str, list] = {}
    for category, group_refs in group_by_category(refs).items():
        specs = []
        for ref in group_refs:
            html = fetch(ref.url, force=force)
            specs.append(parse_page(ref, html))
        specs_by_category[category] = specs
        emit_raw_yaml(category, specs)

    all_specs = [s for specs in specs_by_category.values() for s in specs]
    emit_openapi(all_specs)


@app.command(name="discover")
def discover_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Print the (method, version) inventory; also writes docs/api-inventory.md."""
    _configure_logging(verbose)
    refs = discover()
    emit_inventory(refs)
    for r in refs:
        typer.echo(f"{r.method:40s} {r.version}")


@app.command(name="fetch")
def fetch_cmd(verbose: bool = typer.Option(False, "--verbose", "-v"), force: bool = False) -> None:
    """Run discovery, then fetch every page into the on-disk cache."""
    _configure_logging(verbose)
    refs = discover()
    for r in refs:
        fetch(r.url, force=force)


@app.command(name="parse")
def parse_cmd(url: str, verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Parse one URL (already cached or freshly fetched) and print as YAML."""
    import yaml

    _configure_logging(verbose)
    # url shape: .../docs/{version}/{method}
    parts = url.rstrip("/").split("/")
    method = parts[-1]
    version = parts[-2]
    ref = MethodRef(method=method, version=version)
    html = fetch(ref.url)
    spec = parse_page(ref, html)
    typer.echo(yaml.safe_dump(spec.to_dict(), sort_keys=True, default_flow_style=False))


if __name__ == "__main__":
    app()
