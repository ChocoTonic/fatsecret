# Codegen policy

Files under these paths are AUTO-GENERATED. Do NOT hand-edit:

- `src/fatsecret/models/_generated/`
- `src/fatsecret/resources/_generated/`
- `docs/api-spec/openapi.yaml`
- `docs/api-spec/raw/*.yaml`

Hand edits get clobbered on the next `oas-sync` run. The
`oas-regen-check` CI gate enforces byte-identity between the committed
files and the result of a fresh pipeline run.

## How to add coverage for a new method

1. If the method is missing from the OAS, extend the HTML scraper or
   add the doc URL to the sitemap source under `scripts/oas-sync/`.
2. Run `uv run oas-sync sync` (from `scripts/oas-sync/`) to refresh the
   raw YAMLs and the assembled `docs/api-spec/openapi.yaml`.
3. Run `uv run oas-sync emit-resource <Tag>` to regenerate the resource
   wrapper for the corresponding tag.

## How to add a typed Pydantic model

1. For the supported Platform API, the XSD must declare the response shape. If
   FatSecret's XSD doesn't model it, the method stays as `dict`. We DO NOT
   hand-write Platform API Pydantic models. Use the dict path until upstream XSD
   coverage appears.
2. Add the seed types to `_<resource>_SEED_TYPES` in `emit_models.py`.
3. Run `uv run oas-sync emit-models <resource>`.
4. Add the response shape to `RESPONSE_MODEL_MAP` in
   `scripts/oas-sync/src/oas_sync/model_coverage.py`. This is the single
   source of truth — both the resource codegen and the OAS
   `x-fatsecret-typed-response` vendor extension read from it.
5. Re-run `uv run oas-sync emit-resource <Tag>` and
   `uv run oas-sync assemble` (or `sync`) so the generated wrapper and
   the OAS flag agree.

## Why no hand-written models?

- **Drift**: hand-written models would silently fall out of sync with
  the XSD as FatSecret evolves.
- **Audit**: the codegen pipeline is the single auditable step. Every
  change to the surface flows through it.
- **Determinism**: the `oas-regen-check` CI gate proves the committed
  output matches a fresh run. Hand edits would break that gate.

## Hand-written escape hatches

`src/fatsecret/resources/<name>.py` (NOT `_generated/`) is the place
for per-resource hand-tuned overrides — for example dotted-key
parameter translations, response unwrapping that the codegen can't
infer, or convenience wrappers. These extend the generated class via
subclassing. They are reviewed and preserved across regenerations.

The unofficial authenticated member-website integration is a separate provider
under `src/fatsecret/web/`. It is not represented in the generated Platform OAS
because FatSecret does not document or support its HTML forms as API endpoints.
Its request and response models are necessarily hand-written and must be backed
by parser fixtures, strict parse failures, and mutation readback tests. Do not
import member-website operations into `resources/` or generated API models.

Its public facade contract is manually maintained in
`docs/api-spec/member-web.openapi.yaml`. Changes to that file follow semantic
versioning through `info.version`, are validated in unit tests, and are checked
for breaking changes independently from the generated Platform specification.

## Discovering typed vs dict coverage programmatically

Each operation in `docs/api-spec/openapi.yaml` carries a boolean
`x-fatsecret-typed-response` flag. `true` means the resource wrapper
returns a Pydantic model (or `list[Model]` / `Optional[Model]`);
`false` means the wrapper returns the raw FatSecret response shape as
`dict` / `list[dict]`. The flag is always present — never inferred
from a missing key. The human-facing companion table lives in
`docs/migration-v3.rst`.
