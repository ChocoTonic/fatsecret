"""Deterministic OpenAPI 3.1 assembler.

Reads the per-category raw YAMLs under ``docs/api-spec/raw/`` and writes a
single ``docs/api-spec/openapi.yaml`` file. Pure function over its inputs:
same inputs produce byte-identical output.

No network calls. No LLM. No timestamps. Keys are sorted alphabetically at
every level via a custom yaml Dumper; operations are sorted by operationId.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .config import OUT_RAW_DIR, REPO_ROOT
from .emit_resource import derive_unwrap
from .model_coverage import RESPONSE_MODEL_MAP

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OUT_FINAL_OPENAPI = REPO_ROOT / "docs" / "api-spec" / "openapi.yaml"

# Category YAML filename (without .yaml) → fallback tag used for endpoints that
# do not match a more specific rule in ``_tag_for_endpoint``.
CATEGORY_DEFAULT_TAG = {
    "foods-core": "Foods",
    "foods-aux-and-native": "Foods",
    "recipes": "Recipes",
    "profile-foods": "Profile Foods",
    "saved-meals": "Saved Meals",
    "food-diary": "Food Diary",
    "exercise-weight-profile": "Profile Auth",  # default; overridden by prefix
}

# Hard-coded native / REST-URL endpoints. The crawler's parser could not
# extract these (its regex was foiled by the rendered HTML), so we encode
# them here. Same inputs → same output, so this is still deterministic.
NATIVE_REST_URLS: dict[tuple[str, str], str] = {
    ("natural.language.processing", "v1"): "https://platform.fatsecret.com/rest/natural-language-processing/v1",
    ("image.recognition", "v1"): "https://platform.fatsecret.com/rest/image-recognition/v1",
    ("image.recognition", "v2"): "https://platform.fatsecret.com/rest/image-recognition/v2",
    ("feedback", "v1"): "https://platform.fatsecret.com/rest/feedback/v1",
    # food_entries.get.v2 was historically routed through the REST URL
    # /rest/food-entries/v2, but the hand-written resource calls it
    # method-style ("method": "food_entries.get.v2") and the test suite
    # asserts method-style.  Removed so the assembler classifies it
    # method-style as well.
}

# Methods that POST a JSON body when invoked over the REST-URL style.
NATIVE_POST_METHODS = {
    "natural.language.processing",
    "image.recognition",
    "feedback",
}

# Junk parameter names produced by the upstream HTML parser. They are the
# table column headers / data cells from the docs that aren't actually
# parameter names.
PARAM_NAME_BLACKLIST = {"", "N/A", "String", "---", "Name", "Type", "Description"}


# ---------------------------------------------------------------------------
# Deterministic YAML dumper
# ---------------------------------------------------------------------------


class _SortedDumper(yaml.SafeDumper):
    pass


def _represent_dict_sorted(dumper: yaml.SafeDumper, data: dict) -> Any:
    return dumper.represent_mapping(
        "tag:yaml.org,2002:map", sorted(data.items(), key=lambda kv: kv[0])
    )


_SortedDumper.add_representer(dict, _represent_dict_sorted)


def _dump_yaml(obj: Any) -> str:
    return yaml.dump(
        obj,
        Dumper=_SortedDumper,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
        width=100,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pascal_method(method: str) -> str:
    parts = method.replace(".", "_").split("_")
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def _operation_id(method: str, version: str) -> str:
    return f"{method.replace('.', '_')}_{version}"


def _schema_name(method: str, version: str) -> str:
    return f"{_pascal_method(method)}{version.upper()}Response"


def _api_method_param(method: str, version: str, raw_value: str | None) -> str:
    """Pick the value used in the ``method=`` query string.

    Preference order:
      1. The parsed value from the raw YAML, if set.
      2. ``<method>`` for v1, otherwise ``<method>.<version>``.
    """
    if raw_value:
        return raw_value
    if version == "v1":
        return method
    return f"{method}.{version}"


def _tag_for_endpoint(category: str, method: str) -> str:
    """Map a raw-file category + method name to a human-readable tag."""
    if category == "foods-aux-and-native":
        if method in {"foods.autocomplete", "food.find_id_for_barcode"}:
            return "Foods"
        if method in {"food_brands.get", "food_categories.get", "food_sub_categories.get"}:
            return "Food Classification"
        if method in {"natural.language.processing", "image.recognition"}:
            return "Native APIs"
        if method == "feedback":
            return "Feedback"
        return "Foods"
    if category == "exercise-weight-profile":
        if method.startswith("exercise"):
            return "Exercise Diary"
        if method.startswith("weight"):
            return "Weight Diary"
        if method.startswith("profile"):
            return "Profile Auth"
        return "Profile Auth"
    return CATEGORY_DEFAULT_TAG.get(category, category)


def _normalize_param_type(raw: str | None) -> str:
    if not raw:
        return "string"
    r = raw.strip().lower()
    return {
        "string": "string",
        "int": "integer",
        "long": "integer",
        "decimal": "number",
        "double": "number",
        "boolean": "boolean",
        "date": "string",
    }.get(r, "string")


def _clean_description(raw: str) -> str:
    """Collapse whitespace in descriptions for stable, readable output."""
    if not raw:
        return ""
    return " ".join(raw.split())


def _is_junk_param_name(name: str) -> bool:
    if not name:
        return True
    if "\n" in name:
        return True
    if len(name) > 64:
        # Multi-sentence text leaked from the description column.
        return True
    if name in PARAM_NAME_BLACKLIST:
        return True
    return False


def _build_parameters(
    endpoint: dict[str, Any], is_method_style: bool, api_method_value: str | None
) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    if is_method_style and api_method_value:
        params.append(
            {
                "description": "FatSecret API method selector.",
                "in": "query",
                "name": "method",
                "required": True,
                "schema": {"enum": [api_method_value], "type": "string"},
            }
        )
        seen_names.add("method")

    for raw_p in endpoint.get("parameters") or []:
        name = (raw_p.get("name") or "").strip()
        if _is_junk_param_name(name) or name in seen_names:
            continue
        seen_names.add(name)
        param: dict[str, Any] = {
            "in": "query",
            "name": name,
            "required": bool(raw_p.get("required")),
            "schema": {"type": _normalize_param_type(raw_p.get("type"))},
        }
        desc = _clean_description(raw_p.get("description") or "")
        if desc:
            param["description"] = desc
        params.append(param)

    return params


def _security_for(endpoint: dict[str, Any]) -> list[dict[str, list[str]]]:
    scope = endpoint.get("scope") or "basic"
    oauth_flows = endpoint.get("oauth") or ["oauth1"]
    out: list[dict[str, list[str]]] = []
    if "oauth2" in oauth_flows:
        out.append({"oauth2": [scope]})
    if "oauth1" in oauth_flows:
        out.append({"oauth1": []})
    if not out:
        out.append({"oauth2": [scope]})
    return out


# ---------------------------------------------------------------------------
# Top-level document builders
# ---------------------------------------------------------------------------


def _build_info(global_doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "description": (
            "Community-derived OpenAPI 3.1 specification for the FatSecret Platform API. "
            "Assembled by the scripted oas-sync tool from the per-category raw YAML "
            "files under docs/api-spec/raw/. Not affiliated with FatSecret. "
            "The info.version is a date-style identifier (YYYY.MM) reflecting the "
            "documentation crawl, not a vendor-published API version."
        ),
        "title": "FatSecret Platform API",
        "version": "2026.01",
    }


def _build_servers(global_doc: dict[str, Any]) -> list[dict[str, Any]]:
    base_urls = (global_doc.get("base_urls") or {}) if isinstance(global_doc, dict) else {}
    method_style = base_urls.get("method_style") or "https://platform.fatsecret.com/rest/server.api"
    return [
        {
            "description": "Method-parameter style endpoint. Operations whose path begins with /rest/server.api hang off this server.",
            "url": method_style.rsplit("/rest/server.api", 1)[0] or "https://platform.fatsecret.com",
        },
        {
            "description": "REST-URL style base. Native APIs (NLP, image recognition, feedback) and a few v2 endpoints mount under /rest/...",
            "url": "https://platform.fatsecret.com",
        },
    ]


def _build_security_schemes(global_doc: dict[str, Any]) -> dict[str, Any]:
    oauth2_block = (global_doc.get("oauth2") or {}) if isinstance(global_doc, dict) else {}
    scopes_src = oauth2_block.get("scopes") or {}
    # Deterministic alphabetical order is enforced by the dumper; we just
    # pass the dict through.
    scopes = {str(k): str(v) for k, v in scopes_src.items()} or {
        "basic": "Core API access (food search, recipe lookup, etc.)",
        "premier": "Advanced/premium features and resources",
        "barcode": "Barcode scanning functionality",
        "localization": "Regional/language-specific API calls",
        "nlp": "Natural Language Processing capabilities",
        "image-recognition": "Image-based food recognition features",
        "feedback": "Feedback-related endpoints",
    }
    token_url = oauth2_block.get("token_url") or "https://oauth.fatsecret.com/connect/token"
    return {
        "oauth1": {
            "description": (
                "OAuth 1.0a, HMAC-SHA1 signing. Supports signed (app-context) and "
                "signed+delegated (user-context) requests. PLAINTEXT and RSA-SHA1 "
                "are rejected. See https://platform.fatsecret.com/docs/guides/"
                "authentication/oauth1."
            ),
            "scheme": "oauth",
            "type": "http",
        },
        "oauth2": {
            "description": (
                "OAuth 2.0 client_credentials flow. Tokens are JWT bearer tokens "
                "valid for 24 hours. App-context only — no user-delegated flow."
            ),
            "flows": {
                "clientCredentials": {
                    "scopes": scopes,
                    "tokenUrl": token_url,
                }
            },
            "type": "oauth2",
        },
    }


def _build_error_response(global_doc: dict[str, Any]) -> dict[str, Any]:
    errors = (global_doc.get("errors") or {}) if isinstance(global_doc, dict) else {}
    codes = errors.get("codes") or []
    examples: dict[str, Any] = {}
    for entry in codes:
        if not isinstance(entry, dict):
            continue
        code = entry.get("code")
        if code is None:
            continue
        key = f"code_{code}"
        examples[key] = {
            "summary": f"{entry.get('type', 'Error')} ({code})",
            "value": {
                "error": {
                    "code": int(code) if isinstance(code, (int, str)) and str(code).isdigit() else code,
                    "message": str(entry.get("message", "")),
                }
            },
        }
    return {
        "Error": {
            "content": {
                "application/json": {
                    "examples": examples,
                    "schema": {
                        "properties": {
                            "error": {
                                "properties": {
                                    "code": {
                                        "description": "FatSecret error code (see examples for the full table of 36 codes).",
                                        "type": "integer",
                                    },
                                    "message": {"type": "string"},
                                },
                                "required": ["code", "message"],
                                "type": "object",
                            }
                        },
                        "required": ["error"],
                        "type": "object",
                    },
                }
            },
            "description": "FatSecret error envelope. The `error.code` is one of 36 documented codes; see examples.",
        }
    }


def _response_schema_from_block(block: Any) -> dict[str, Any]:
    """Convert a (possibly nested) raw `response` mapping into a JSON-Schema-y
    flat representation. We don't try to be clever — just walk the structure
    and tag each leaf as a string field. The goal is to give codegen a stable
    handle, not to produce a perfectly typed schema. Deduplication and proper
    typing are deferred to a later pass.
    """
    if not isinstance(block, dict) or not block:
        return {"additionalProperties": True, "type": "object"}

    properties: dict[str, Any] = {}
    for key, value in block.items():
        if isinstance(value, dict):
            properties[str(key)] = _response_schema_from_block(value)
        elif isinstance(value, list):
            # Treat as array of objects/strings.
            if value and isinstance(value[0], dict):
                properties[str(key)] = {
                    "items": _response_schema_from_block(value[0]),
                    "type": "array",
                }
            else:
                properties[str(key)] = {"items": {"type": "string"}, "type": "array"}
        else:
            # Type leaf scalars by their Python value so codegen's
            # ``derive_unwrap`` can spot the integer ``success`` flag that marks
            # a mutator endpoint.  All other scalar shapes stay as ``string``.
            if isinstance(value, bool):
                properties[str(key)] = {"type": "boolean"}
            elif isinstance(value, int):
                properties[str(key)] = {"type": "integer"}
            elif isinstance(value, float):
                properties[str(key)] = {"type": "number"}
            else:
                properties[str(key)] = {"type": "string"}
    return {"properties": properties, "type": "object"}


# ---------------------------------------------------------------------------
# Loading raw inputs
# ---------------------------------------------------------------------------


def _load_global(raw_dir: Path) -> dict[str, Any]:
    path = raw_dir / "_global.yaml"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def _load_endpoints(raw_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Return (category, endpoint) tuples for every per-category raw file."""
    out: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(raw_dir.glob("*.yaml")):
        category = path.stem
        if category == "_global":
            continue
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        for ep in data.get("endpoints") or []:
            if isinstance(ep, dict):
                out.append((category, ep))
    return out


# ---------------------------------------------------------------------------
# Operation builder
# ---------------------------------------------------------------------------


def _build_operation(
    category: str, endpoint: dict[str, Any], schemas: dict[str, Any]
) -> tuple[str, str, dict[str, Any]]:
    """Return (path, http_verb, operation_object)."""
    method = str(endpoint.get("method") or "")
    version = str(endpoint.get("version") or "v1")
    op_id = _operation_id(method, version)
    summary = f"{method} ({version})"

    native_url = NATIVE_REST_URLS.get((method, version)) or endpoint.get("rest_url")
    is_method_style = native_url is None

    if is_method_style:
        api_method_value = _api_method_param(method, version, endpoint.get("api_method_param"))
        path = f"/rest/server.api#{api_method_value}"
        verb = (endpoint.get("http_verb") or "GET").lower()
    else:
        api_method_value = None
        path = native_url
        if method in NATIVE_POST_METHODS:
            verb = "post"
        else:
            verb = (endpoint.get("http_verb") or "GET").lower()

    parameters = _build_parameters(endpoint, is_method_style, api_method_value)

    # Response schema: register one schema per operation, flat.
    schema_name = _schema_name(method, version)
    response_schema = _response_schema_from_block(endpoint.get("response"))
    schemas[schema_name] = response_schema

    responses: dict[str, Any] = {
        "200": {
            "content": {
                "application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}
            },
            "description": "Successful response.",
        },
        "default": {"$ref": "#/components/responses/Error"},
    }

    tag = _tag_for_endpoint(category, method)
    unwrap_path, list_key, _is_mutator = derive_unwrap(response_schema)
    has_typed_model = (tag, tuple(unwrap_path), list_key) in RESPONSE_MODEL_MAP

    operation: dict[str, Any] = {
        "operationId": op_id,
        "responses": responses,
        "security": _security_for(endpoint),
        "summary": summary,
        "tags": [tag],
        # Machine-readable companion to the typed/dict split documented for
        # humans in docs/migration-v3.rst.  Always emitted (boolean) so
        # programmatic consumers can discover coverage without inferring
        # from a missing key. Source of truth: model_coverage.py.
        "x-fatsecret-typed-response": has_typed_model,
    }
    if parameters:
        operation["parameters"] = parameters
    if endpoint.get("deprecated"):
        operation["deprecated"] = True
    if endpoint.get("premier"):
        operation["x-fatsecret-premier"] = True
    if endpoint.get("notes"):
        operation["description"] = _clean_description(str(endpoint["notes"]))

    if not is_method_style and verb == "post":
        operation["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {"additionalProperties": True, "type": "object"}
                }
            },
            "required": True,
        }

    return path, verb, operation


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_openapi_document(raw_dir: Path = OUT_RAW_DIR) -> dict[str, Any]:
    global_doc = _load_global(raw_dir)
    endpoints = _load_endpoints(raw_dir)

    schemas: dict[str, Any] = {}

    # path → verb → operation, but we may have multiple operations on the
    # same (path, verb) only across the legacy method= hack — guarded by the
    # ``#<api_method>`` fragment in the path, so each path key is unique to
    # one operation. The REST-URL paths (NLP/image-recognition/feedback) are
    # also unique by version.
    operations: list[tuple[str, str, dict[str, Any]]] = []
    for category, endpoint in endpoints:
        operations.append(_build_operation(category, endpoint, schemas))

    # Sort by operationId for stable emission.
    operations.sort(key=lambda t: t[2]["operationId"])

    paths: dict[str, dict[str, Any]] = {}
    for path, verb, op in operations:
        bucket = paths.setdefault(path, {})
        if verb in bucket:
            # Should never happen given the path-fragment trick; log if it
            # does and keep the first.
            log.warning(
                "collision at %s %s for operationId=%s — keeping first",
                verb,
                path,
                op["operationId"],
            )
            continue
        bucket[verb] = op

    document: dict[str, Any] = {
        "components": {
            "responses": _build_error_response(global_doc),
            "schemas": schemas,
            "securitySchemes": _build_security_schemes(global_doc),
        },
        "info": _build_info(global_doc),
        "openapi": "3.1.0",
        "paths": paths,
        "security": [{"oauth2": ["basic"]}, {"oauth1": []}],
        "servers": _build_servers(global_doc),
        "tags": [
            {"description": "Foods search, food.get, autocomplete, barcode.", "name": "Foods"},
            {"description": "Brands, categories, sub-categories.", "name": "Food Classification"},
            {"description": "Recipe retrieval, search, favorites.", "name": "Recipes"},
            {"description": "User-scoped food creation, favorites, eaten lists.", "name": "Profile Foods"},
            {"description": "User-scoped saved meals and saved-meal-items CRUD.", "name": "Saved Meals"},
            {"description": "Daily food diary entries and monthly summaries.", "name": "Food Diary"},
            {"description": "Exercise catalog and diary entries.", "name": "Exercise Diary"},
            {"description": "Weight tracking endpoints.", "name": "Weight Diary"},
            {"description": "Profile creation and authentication retrieval.", "name": "Profile Auth"},
            {"description": "REST-URL native APIs: NLP and image recognition.", "name": "Native APIs"},
            {"description": "Issue/feedback reporting.", "name": "Feedback"},
        ],
    }

    return document


def write_openapi(path: Path = OUT_FINAL_OPENAPI, raw_dir: Path = OUT_RAW_DIR) -> Path:
    document = build_openapi_document(raw_dir=raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_yaml(document), encoding="utf-8")
    log.info("wrote %s", path)
    return path


def run_redocly_lint(path: Path) -> tuple[bool, str]:
    """Run ``redocly lint <path>`` if available. Returns (ran, output)."""
    if shutil.which("redocly") is None:
        log.info("redocly not installed — skipping lint")
        return False, "redocly not installed"
    try:
        proc = subprocess.run(
            ["redocly", "lint", str(path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return True, "redocly lint timed out after 60s"
    output = (proc.stdout or "") + (proc.stderr or "")
    log.info("redocly exit=%d", proc.returncode)
    return True, output


def assemble(lint: bool = True) -> Path:
    """Assemble the final OpenAPI document and optionally run redocly lint."""
    path = write_openapi()
    if lint:
        ran, out = run_redocly_lint(path)
        if ran:
            log.info("redocly output:\n%s", out)
    return path
