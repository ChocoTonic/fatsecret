# oas-sync

Deterministic crawler that derives an OpenAPI 3.1 spec from FatSecret's
published documentation at `platform.fatsecret.com/docs/v*/{method}`.

This exists because FatSecret does not publish a machine-readable spec
and ships new versions of individual endpoints over time. Re-running this
script on a schedule (or after a version bump) keeps `docs/api-spec/` in
sync with upstream without LLM round-trips.

## Why deterministic?

- Fixed dependency versions (`uv lock`).
- HTML cached to `.cache/` by URL hash; replays produce byte-identical output.
- All YAML output uses sorted keys; no timestamps in artifacts.
- No LLMs, no fuzzy extraction — CSS selectors against a stable docs DOM.

## Usage

```sh
cd scripts/oas-sync
uv sync
uv run oas-sync sync               # full discover → fetch → parse → emit
uv run oas-sync discover           # just the (method, version) inventory
uv run oas-sync fetch               # fetch + cache only
uv run oas-sync parse <url>        # parse a single cached page for debugging
```

Output paths (relative to repo root):
- `docs/api-inventory.md` — list of every documented (method, version) pair
- `docs/api-spec/raw/*.yaml` — per-category structured extraction
- `docs/api-spec/openapi.generated.yaml` — minimal OpenAPI 3.1 spec derived
  from the raw YAMLs. Written to a `.generated.` path on purpose: the
  canonical hand-curated `docs/api-spec/openapi.yaml` is richer (full
  response schemas, security overrides, error examples). Treat the
  generated file as a **drift detector**: when it diverges from the
  canonical file, FatSecret likely shipped a docs change worth reviewing.

## When the DOM changes

FatSecret's docs site is server-rendered. If the selectors in `parse.py`
stop matching, the script will emit a row with `parse_warnings: [...]`
rather than silently dropping data. Run `oas-sync parse <url>` against
the offending URL to iterate on selectors.

## What this does NOT do

- Does not infer schemas from response examples beyond what the docs page
  declares. If a field is missing from the docs, it's missing from the
  spec.
- Does not call live API endpoints. Source of truth is the docs site only.
