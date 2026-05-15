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
    # Food Classification: strip the ``food_`` family prefix; leave the
    # ``brands_get`` / ``categories_get`` / ``sub_categories_get`` suffix so
    # each method keeps a unique name.
    "Food Classification": ("food_",),
    # Recipes: strip only the ``recipes_`` / ``recipe_`` prefix so that
    # ``recipe.get`` becomes ``get_v1`` and ``recipe_types.get`` becomes
    # ``types_get_v1`` rather than colliding on ``get_v1``.
    "Recipes": ("recipes_", "recipe_"),
    "Profile Foods": ("foods_", "food_"),
    # Saved Meals: strip the longest available prefix so that
    # ``saved_meal.create`` -> ``create_v1`` and
    # ``saved_meal_item.add`` -> ``item_add_v1`` / ``items_get_v1``.
    "Saved Meals": ("saved_meals_", "saved_meal_"),
    # Food Diary / Exercise Diary: keep the ``entries_`` / ``entry_`` /
    # ``exercises_`` discriminator after stripping the resource prefix, so
    # ``food_entry.create`` -> ``entry_create_v1`` (not ``create_v1``).
    "Food Diary": ("food_",),
    "Exercise Diary": ("exercise_",),
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
# Phase 2: response-model wrapping registry
# ---------------------------------------------------------------------------
#
# Maps (tag, unwrap_path_tuple, list_key) -> (model_module, model_class).
# When an entry exists, the generated method wraps the unwrapped raw
# payload in ``Model.model_validate(raw)`` (singular) or
# ``[Model.model_validate(r) for r in raw]`` (list), and the return type
# annotation becomes the model class instead of ``Any``/``list``.
#
# Resources without XSD coverage (food_classification, saved_meals,
# weight_diary's non-month endpoints, native_apis, feedback) have no
# entries here and continue to return raw ``dict``/``list[dict]``.
#
# ``model_module`` is the name of the file under
# ``fatsecret.models._generated`` (also re-exported via
# ``fatsecret.models``).
_RESPONSE_MODEL_MAP: dict[
    tuple[str, tuple[str, ...], str | None],
    tuple[str, str],
] = {
    # Foods (singular)
    ("Foods", ("food",), None): ("foods", "Food"),
    # Foods (list / search variants)
    ("Foods", ("foods",), "food"): ("foods", "Food"),
    ("Foods", ("foods_search", "results"), "food"): ("foods", "Food"),
    # Profile Foods (same Food model)
    ("Profile Foods", ("foods",), "food"): ("foods", "Food"),
    # Recipes
    ("Recipes", ("recipe",), None): ("recipes", "RecipesRecipe"),
    ("Recipes", ("recipes",), "recipe"): ("recipes", "RecipesRecipe"),
    # Profile Auth
    ("Profile Auth", ("profile",), None): ("profile_auth", "Profile"),
    # Food Diary
    ("Food Diary", ("food_entries",), "food_entry"): ("food_diary", "FoodEntry"),
    ("Food Diary", ("month",), "day"): ("food_diary", "Day"),
    # Exercise Diary
    ("Exercise Diary", ("exercise_entries",), "exercise_entry"): (
        "exercise_diary", "ExerciseEntry",
    ),
    ("Exercise Diary", ("exercise_types",), "exercise"): (
        "exercise_diary", "Exercise",
    ),
    ("Exercise Diary", ("month",), "day"): ("exercise_diary", "Day"),
    # Weight Diary (only get_month is XSD-covered)
    ("Weight Diary", ("month",), "day"): ("weight_diary", "Day"),
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


_METHOD_NAME_OVERRIDES: dict[tuple[str, str], str] = {
    # operation_id after prefix-stripping -> canonical hand-written name.
    ("Exercise Diary", "exercises_get_v1"): "list_v1",
    ("Exercise Diary", "exercises_get_v2"): "list_v2",
    ("Feedback", "feedback_v1"): "submit_v1",
}


def _method_name_for(tag: str, operation_id: str) -> str:
    stripped = operation_id
    for p in _TAG_PREFIXES.get(tag, ()):
        if operation_id.startswith(p):
            stripped = operation_id[len(p):]
            break
    return _METHOD_NAME_OVERRIDES.get((tag, stripped), stripped)


def _param_type_hint(param: dict[str, Any]) -> str:
    schema = param.get("schema") or {}
    t = schema.get("type", "string")
    return _TYPE_MAP.get(t, "str")


def _is_date_param(param: dict[str, Any]) -> bool:
    name = param.get("name") or ""
    if name == "date" or name.endswith("_date"):
        # The extractor maps any arg whose annotation includes datetime/date
        # to raw type ``Date``, but the assembler lowers Date → ``string`` so
        # we also recognise the conventional ``date`` / ``*_date`` naming used
        # throughout the hand-written resources.
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
        wire = p.get("name")
        if wire in ("method", "format"):
            continue
        # Translate dotted wire names (e.g. ``calories.from``) to Python-safe
        # arg names (``calories_from``).  The arg is what appears in the
        # signature; the wire goes in the params dict.
        arg = (wire or "").replace(".", "_")
        item = {
            "arg": arg,
            "wire": wire,
            "type": _param_type_hint(p),
            "is_date": _is_date_param(p),
        }
        (required if p.get("required") else optional).append(item)

    responses = operation.get("responses") or {}
    ok = responses.get("200") or {}
    content = (ok.get("content") or {}).get("application/json") or {}
    schema = _resolve_schema(oas, content.get("schema") or {})
    unwrap_path, list_key, is_mutator = derive_unwrap(schema)

    model = _RESPONSE_MODEL_MAP.get((tag, tuple(unwrap_path), list_key))
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
        # (model_module, model_class) when this method's response is
        # XSD-modelled; ``None`` when it falls back to a raw dict.
        "model": model,
    }


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _render_method(m: dict[str, Any]) -> str:
    buf = StringIO()
    name = m["method_name"]

    # Return type hint.
    model = m.get("model")
    if m["is_mutator"]:
        ret = "bool"
    elif model is not None and m["list_key"]:
        ret = f"list[{model[1]}]"
    elif model is not None:
        ret = f"Optional[{model[1]}]"
    elif m["list_key"]:
        ret = "list"
    else:
        ret = "Any"

    # Signature.
    buf.write(f"    def {name}(\n")
    buf.write("        self,\n")
    for p in m["required_params"]:
        buf.write(f"        {p['arg']}: {p['type']},\n")
    for p in m["optional_params"]:
        buf.write(f"        {p['arg']}: Optional[{p['type']}] = None,\n")
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
                f'        {container}["{p["wire"]}"] = '
                f"self._client.unix_time_v2({p['arg']})\n"
            )
        else:
            buf.write(f'        {container}["{p["wire"]}"] = {p["arg"]}\n')

    if m["optional_params"]:
        buf.write("        self._client._set_optional(\n")
        buf.write(f"            {container},\n")
        buf.write("            [\n")
        for p in m["optional_params"]:
            if p["is_date"]:
                buf.write(
                    f'                ("{p["wire"]}", None if {p["arg"]} is None '
                    f"else self._client.unix_time_v2({p['arg']})),\n"
                )
            else:
                buf.write(f'                ("{p["wire"]}", {p["arg"]}),\n')
        buf.write("            ],\n")
        buf.write("        )\n")

    if m["is_rest_url"]:
        buf.write(
            f'        payload = self._client._call('
            f'{{}}, url="{m["rest_url"]}", method="{m["http_verb"]}", '
            f"json_body=body)\n"
        )
    else:
        # Method-style endpoints default to GET; only emit the kwarg when the
        # raw YAML specifies a mutating verb so the existing GET callsites are
        # unchanged.
        verb = m["http_verb"]
        if verb and verb.upper() not in {"GET", ""}:
            buf.write(
                f'        payload = self._client._call(params, method="{verb}")\n'
            )
        else:
            buf.write("        payload = self._client._call(params)\n")

    # Return.
    path_args = "".join(f', "{k}"' for k in m["unwrap_path"])
    if m["is_mutator"]:
        # ``_mutator_success`` inspects the payload for a top-level ``success``
        # key.  Pass ``payload`` straight through rather than pre-unwrapping;
        # otherwise we hand it a bare scalar and the helper short-circuits to
        # passthrough.
        buf.write("        return self._client._mutator_success(payload)\n")
    elif m["list_key"]:
        buf.write(
            f"        raw = self._client._unwrap(payload{path_args}, "
            f'list_key="{m["list_key"]}")\n'
        )
        if model is not None:
            buf.write(
                f"        return [{model[1]}.model_validate(r) for r in raw]\n"
            )
        else:
            buf.write("        return raw\n")
    elif m["unwrap_path"]:
        buf.write(f"        raw = self._client._unwrap(payload{path_args})\n")
        if model is not None:
            buf.write("        if raw is None:\n")
            buf.write("            return None\n")
            buf.write(
                f"        return {model[1]}.model_validate(raw)\n"
            )
        else:
            buf.write("        return raw\n")
    else:
        if model is not None:
            buf.write(
                f"        return {model[1]}.model_validate(payload)\n"
            )
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
    buf.write("from .._base import BaseResource\n")
    # Emit model imports grouped by module, sorted for determinism.
    model_imports: dict[str, set[str]] = {}
    for m in methods:
        model = m.get("model")
        if model is not None:
            model_imports.setdefault(model[0], set()).add(model[1])
    if model_imports:
        buf.write("\n")
        for module in sorted(model_imports):
            classes = ", ".join(sorted(model_imports[module]))
            buf.write(
                f"from ...models._generated.{module} import {classes}\n"
            )
    buf.write("\n\n")
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
