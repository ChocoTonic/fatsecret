"""OAS-driven resource codegen.

Reads ``docs/api-spec/openapi.yaml``, groups operations by ``tags[0]``, and
emits one resource Python module per tag. The pilot for v2.0 Phase 2 is the
``Foods`` tag, written to ``src/fatsecret/resources/_generated/foods.py``.

The unwrap path is *schema-derived*: we walk the response schema's
single-property chain to find the user-meaningful data. See
``derive_unwrap`` for the algorithm. No ``x-fatsecret-*`` extensions are
consulted.

The renderer is a hand-rolled Python string builder. We tried Jinja2 first
and found whitespace control too brittle for nested control flow. A
single-purpose builder is shorter and easier to audit.
"""

from __future__ import annotations

import logging
import re
from io import StringIO
from pathlib import Path
from typing import Any

import yaml

from .config import REPO_ROOT

log = logging.getLogger(__name__)


OAS_PATH = REPO_ROOT / "docs" / "api-spec" / "openapi.yaml"
GEN_DIR = REPO_ROOT / "src" / "fatsecret" / "resources" / "_generated"


_TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
}


_TAG_PREFIXES: dict[str, tuple[str, ...]] = {
    "Foods": ("foods_", "food_"),
    "Food Classification": (
        "food_sub_categories_",
        "food_categories_",
        "food_brands_",
    ),
    "Recipes": ("recipes_", "recipe_types_", "recipe_"),
    "Profile Foods": ("foods_", "food_"),
    "Saved Meals": ("saved_meal_items_", "saved_meal_", "saved_meals_"),
    "Food Diary": ("food_entries_", "food_entry_"),
    "Exercise Diary": ("exercise_entries_", "exercise_entry_", "exercises_"),
    "Weight Diary": ("weights_", "weight_"),
    "Profile Auth": ("profile_",),
    "Native APIs": (),
    "Feedback": (),
}


_TAG_SLUG_MAP = {
    "Foods": "foods",
    "Food Classification": "classification",
    "Recipes": "recipes",
    "Profile Foods": "profile_foods",
    "Saved Meals": "meals",
    "Food Diary": "diary",
    "Exercise Diary": "exercises",
    "Weight Diary": "weight",
    "Profile Auth": "profile",
    "Native APIs": "native",
    "Feedback": "feedback",
}


# ---------------------------------------------------------------------------
# OAS loading
# ---------------------------------------------------------------------------


def load_oas(path: Path = OAS_PATH) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _resolve_ref(oas: dict[str, Any], ref: str) -> dict[str, Any]:
    assert ref.startswith("#/"), f"only local refs supported, got {ref}"
    cur: Any = oas
    for part in ref[2:].split("/"):
        cur = cur[part]
    return cur


def _resolve_schema(oas: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    while isinstance(schema, dict) and "$ref" in schema:
        schema = _resolve_ref(oas, schema["$ref"])
    return schema


# ---------------------------------------------------------------------------
# Unwrap derivation (the heart of Phase 2)
# ---------------------------------------------------------------------------


def derive_unwrap(schema: dict[str, Any]) -> tuple[tuple[str, ...], str | None, bool]:
    """Walk a response schema's single-property chain.

    Returns ``(path, list_key, is_mutator)``:

      * ``path`` — tuple of keys to traverse into the payload.
      * ``list_key`` — if the chain ends at an array property, the property
        name that carries the array. ``_unwrap`` uses it to coerce single-dict
        responses into ``list[dict]``.
      * ``is_mutator`` — True when the chain ends at a ``success`` integer
        property; the generated method should return a bool.
    """
    cur = schema
    path: list[str] = []
    while (
        isinstance(cur, dict)
        and cur.get("type") == "object"
        and len(cur.get("properties") or {}) == 1
    ):
        key, child = next(iter(cur["properties"].items()))
        if not isinstance(child, dict):
            break
        if child.get("type") == "array":
            return tuple(path), key, False
        if child.get("type") == "integer" and key == "success":
            return tuple(path + [key]), None, True
        path.append(key)
        cur = child
    return tuple(path), None, False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _method_name_for(tag: str, operation_id: str) -> str:
    for p in _TAG_PREFIXES.get(tag, ()):
        if operation_id.startswith(p):
            return operation_id[len(p):]
    return operation_id


def _param_type_hint(param: dict[str, Any]) -> str:
    schema = param.get("schema") or {}
    t = schema.get("type", "string")
    return _TYPE_MAP.get(t, "str")


def _is_date_param(param: dict[str, Any]) -> bool:
    if param.get("name") == "date":
        return True
    schema = param.get("schema") or {}
    return schema.get("format") == "date"


def _api_method_value(parameters: list[dict[str, Any]]) -> str | None:
    for p in parameters:
        if p.get("name") == "method":
            schema = p.get("schema") or {}
            enum = schema.get("enum") or []
            if enum:
                return enum[0]
    return None


def _is_rest_url(path: str) -> bool:
    return not path.startswith("/rest/server.api")


def _docstring_for(operation: dict[str, Any]) -> str:
    parts: list[str] = []
    summary = operation.get("summary") or ""
    description = operation.get("description") or ""
    if summary:
        parts.append(summary + (".") if not summary.endswith(".") else summary)
    if description:
        parts.append(description)
    if operation.get("deprecated"):
        parts.append("DEPRECATED upstream.")
    if operation.get("x-fatsecret-premier"):
        parts.append("Premier-only.")
    return " ".join(parts).strip() or "Auto-generated method."


def _tag_slug(tag: str) -> str:
    if tag in _TAG_SLUG_MAP:
        return _TAG_SLUG_MAP[tag]
    return re.sub(r"\W+", "_", tag.lower()).strip("_")


def _class_name(tag: str) -> str:
    slug = _tag_slug(tag)
    return "".join(p.capitalize() for p in slug.split("_")) + "Resource"


# ---------------------------------------------------------------------------
# Per-operation model
# ---------------------------------------------------------------------------


def _extract_method(
    oas: dict[str, Any],
    path: str,
    verb: str,
    operation: dict[str, Any],
    tag: str,
) -> dict[str, Any] | None:
    op_id = operation.get("operationId")
    if not op_id:
        return None

    parameters = operation.get("parameters") or []
    required: list[dict[str, Any]] = []
    optional: list[dict[str, Any]] = []
    for p in parameters:
        name = p.get("name")
        if name in ("method", "format"):
            continue
        item = {
            "name": name,
            "type": _param_type_hint(p),
            "is_date": _is_date_param(p),
        }
        (required if p.get("required") else optional).append(item)

    responses = operation.get("responses") or {}
    ok = responses.get("200") or {}
    content = (ok.get("content") or {}).get("application/json") or {}
    schema = _resolve_schema(oas, content.get("schema") or {})
    unwrap_path, list_key, is_mutator = derive_unwrap(schema)

    return {
        "method_name": _method_name_for(tag, op_id),
        "operation_id": op_id,
        "api_method_value": _api_method_value(parameters),
        "is_rest_url": _is_rest_url(path),
        "rest_url": path if _is_rest_url(path) else None,
        "http_verb": verb.upper(),
        "required_params": required,
        "optional_params": optional,
        "unwrap_path": list(unwrap_path),
        "list_key": list_key,
        "is_mutator": is_mutator,
        "docstring": _docstring_for(operation),
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _render_method(m: dict[str, Any]) -> str:
    buf = StringIO()
    name = m["method_name"]

    # Return type hint.
    if m["is_mutator"]:
        ret = "bool"
    elif m["list_key"]:
        ret = "list"
    else:
        ret = "Any"

    # Signature.
    buf.write(f"    def {name}(\n")
    buf.write("        self,\n")
    for p in m["required_params"]:
        buf.write(f"        {p['name']}: {p['type']},\n")
    for p in m["optional_params"]:
        buf.write(f"        {p['name']}: Optional[{p['type']}] = None,\n")
    buf.write(f"    ) -> {ret}:\n")

    # Docstring.
    doc = m["docstring"].replace('"""', "'''")
    buf.write(f'        """{doc}"""\n')

    # Body.
    if m["is_rest_url"]:
        container = "body"
        buf.write("        body: dict[str, Any] = {}\n")
    else:
        container = "params"
        buf.write(
            f'        params: dict[str, Any] = {{"method": "{m["api_method_value"]}"}}\n'
        )

    for p in m["required_params"]:
        if p["is_date"]:
            buf.write(
                f'        {container}["{p["name"]}"] = '
                f"self._client.unix_time_v2({p['name']})\n"
            )
        else:
            buf.write(f'        {container}["{p["name"]}"] = {p["name"]}\n')

    if m["optional_params"]:
        buf.write("        self._client._set_optional(\n")
        buf.write(f"            {container},\n")
        buf.write("            [\n")
        for p in m["optional_params"]:
            if p["is_date"]:
                buf.write(
                    f'                ("{p["name"]}", None if {p["name"]} is None '
                    f"else self._client.unix_time_v2({p['name']})),\n"
                )
            else:
                buf.write(f'                ("{p["name"]}", {p["name"]}),\n')
        buf.write("            ],\n")
        buf.write("        )\n")

    if m["is_rest_url"]:
        buf.write(
            f'        payload = self._client._call('
            f'{{}}, url="{m["rest_url"]}", method="{m["http_verb"]}", '
            f"json_body=body)\n"
        )
    else:
        buf.write("        payload = self._client._call(params)\n")

    # Return.
    path_args = "".join(f', "{k}"' for k in m["unwrap_path"])
    if m["is_mutator"]:
        buf.write(
            f"        return self._client._mutator_success("
            f"self._client._unwrap(payload{path_args}))\n"
        )
    elif m["list_key"]:
        buf.write(
            f"        return self._client._unwrap(payload{path_args}, "
            f'list_key="{m["list_key"]}")\n'
        )
    elif m["unwrap_path"]:
        buf.write(f"        return self._client._unwrap(payload{path_args})\n")
    else:
        buf.write("        return payload\n")

    return buf.getvalue()


def _render_module(tag: str, methods: list[dict[str, Any]]) -> str:
    class_name = _class_name(tag)
    buf = StringIO()
    buf.write(
        f"# AUTO-GENERATED by scripts/oas-sync emit-resource {tag}. "
        "Do not edit by hand.\n"
    )
    buf.write(f'"""Resource wrapper for the OAS ``{tag}`` tag (generated)."""\n\n')
    buf.write("from __future__ import annotations\n\n")
    buf.write("from typing import Any, Optional\n\n")
    buf.write("from .._base import BaseResource\n\n\n")
    buf.write(f"class {class_name}(BaseResource):\n")
    buf.write(f'    """Resource methods for the OAS `{tag}` tag (generated)."""\n')
    for m in methods:
        buf.write("\n")
        buf.write(_render_method(m))
    buf.write(f'\n\n__all__ = ["{class_name}"]\n')
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Top-level entrypoint
# ---------------------------------------------------------------------------


def emit_resource(tag: str, out_path: Path | None = None) -> Path:
    """Generate the resource module for `tag`. Returns the written path."""
    oas = load_oas()
    paths = oas.get("paths") or {}

    methods: list[dict[str, Any]] = []
    for path, verbs in paths.items():
        if not isinstance(verbs, dict):
            continue
        for verb, operation in verbs.items():
            if not isinstance(operation, dict):
                continue
            tags = operation.get("tags") or []
            if not tags or tags[0] != tag:
                continue
            m = _extract_method(oas, path, verb, operation, tag)
            if m is not None:
                methods.append(m)

    methods.sort(key=lambda m: m["method_name"])

    rendered = _render_module(tag, methods)

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    init_file = GEN_DIR / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Generated resource modules."""\n', encoding="utf-8")

    final = out_path or (GEN_DIR / f"{_tag_slug(tag)}.py")
    final.write_text(rendered, encoding="utf-8")
    log.info("wrote %s (%d methods)", final, len(methods))
    return final
