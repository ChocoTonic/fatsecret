"""Sphinx extension: group ``fatsecret.Fatsecret`` API methods by OpenAPI tag.

Reads ``docs/api-spec/openapi.generated.yaml`` at build time, maps each OAS
operationId to its concrete Python method, and emits one section per tag.

Supports both API surface shapes used across the v1.x line:

* **Namespaced** (v1.6+): methods live on resource sub-objects
  (e.g. ``Fatsecret.foods.search_v5``). Detected when one or more
  ``BaseResource``-like attributes are found on a ``Fatsecret`` instance.
* **Flat** (v1.0 - v1.5): methods live directly on the ``Fatsecret`` class
  (e.g. ``Fatsecret.foods_search_v5``). Used as fallback when no resource
  sub-objects are found.

Falls back to a flat ``autoclass`` block if the spec or pyyaml is missing.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Optional

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList

# OAS tag -> ordered list of Python resource attribute names to search.
# First match wins. Covers every tag in openapi.generated.yaml as of 2026-05.
_TAG_TO_RESOURCES: dict[str, list[str]] = {
    "food": ["foods", "profile_foods"],
    "foods": ["foods", "profile_foods"],
    "food_brands": ["classification"],
    "food_categories": ["classification"],
    "food_sub_categories": ["classification"],
    "food_entries": ["diary"],
    "food_entry": ["diary"],
    "exercises": ["exercises"],
    "exercise_entries": ["exercises"],
    "exercise_entry": ["exercises"],
    "recipe": ["recipes"],
    "recipes": ["recipes"],
    "recipe_types": ["recipes"],
    "saved_meal": ["meals"],
    "saved_meals": ["meals"],
    "saved_meal_item": ["meals"],
    "saved_meal_items": ["meals"],
    "weight": ["weight"],
    "weights": ["weight"],
    "image": ["native"],
    "natural": ["native"],
    "profile": ["profile", "profile_foods"],
    "feedback": ["feedback"],
}

_TAG_HEADING: dict[str, str] = {
    "food": "Food",
    "foods": "Foods (search, autocomplete, favorites)",
    "food_brands": "Food Brands",
    "food_categories": "Food Categories",
    "food_sub_categories": "Food Sub-Categories",
    "food_entries": "Food Diary Entries",
    "food_entry": "Food Diary Entry",
    "exercises": "Exercises",
    "exercise_entries": "Exercise Diary Entries",
    "exercise_entry": "Exercise Diary Entry",
    "recipe": "Recipe",
    "recipes": "Recipes",
    "recipe_types": "Recipe Types",
    "saved_meal": "Saved Meal",
    "saved_meals": "Saved Meals",
    "saved_meal_item": "Saved Meal Item",
    "saved_meal_items": "Saved Meal Items",
    "weight": "Weight",
    "weights": "Weights (history)",
    "image": "Image Recognition",
    "natural": "Natural Language Processing",
    "profile": "Profile",
    "feedback": "Feedback",
}

# Explicit overrides where the operationId does not derive from any
# (resource, method) substring (renamed for clarity in the namespaced
# Python surface). Ignored when the resource is not present (flat shape).
_OP_OVERRIDES: dict[str, tuple[str, str]] = {
    "exercises_get_v1": ("exercises", "list_v1"),
    "exercises_get_v2": ("exercises", "list_v2"),
    "feedback_v1": ("feedback", "submit_v1"),
}


_log = logging.getLogger(__name__)


def _load_spec(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        import yaml  # type: ignore
    except ImportError:
        _log.warning("fatsecret_oas: pyyaml not installed; falling back to flat autoclass")
        return None
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception as exc:
        _log.warning("fatsecret_oas: failed to parse %s: %s", path, exc)
        return None


def _collect_ops(spec: dict) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for _path, pathitem in (spec.get("paths") or {}).items():
        if not isinstance(pathitem, dict):
            continue
        for _method, op in pathitem.items():
            if not isinstance(op, dict) or "operationId" not in op:
                continue
            primary = op.get("tags") or ["Untagged"]
            for tag in primary:
                groups[tag].append(op["operationId"])
            for sub in op.get("x-fatsecret-additional-operations") or []:
                if not isinstance(sub, dict) or "operationId" not in sub:
                    continue
                for tag in sub.get("tags") or primary:
                    groups[tag].append(sub["operationId"])
    return groups


def _resource_inventory(cls) -> tuple[dict[str, set[str]], dict[str, type]]:
    """Return ``({attr: {method, ...}}, {attr: ResourceClass})``."""
    try:
        fs = cls("_docs_consumer_key", "_docs_consumer_secret")
    except Exception:
        return {}, {}
    try:
        from fatsecret.resources._base import BaseResource  # type: ignore
    except Exception:
        BaseResource = None  # type: ignore
    methods: dict[str, set[str]] = {}
    classes: dict[str, type] = {}
    for name in dir(fs):
        if name.startswith("_"):
            continue
        try:
            val = getattr(fs, name)
        except Exception:
            continue
        if BaseResource is not None and not isinstance(val, BaseResource):
            continue
        if BaseResource is None and not hasattr(val, "_client"):
            continue
        methods[name] = {
            m for m in dir(val)
            if not m.startswith("_") and callable(getattr(val, m, None))
        }
        classes[name] = type(val)
    return methods, classes


def _flat_methods(cls) -> set[str]:
    """All public callable attributes defined directly on ``cls``."""
    out: set[str] = set()
    for name in dir(cls):
        if name.startswith("_"):
            continue
        try:
            val = getattr(cls, name)
        except Exception:
            continue
        if callable(val):
            out.add(name)
    return out


def _candidate_method_names(op_id: str, tag: str) -> list[str]:
    """Generate plausible Python method names for ``op_id`` under ``tag``.

    OAS operationIds tend to be ``<tag>_<method>`` but the Python resource
    name does not always equal the tag (e.g. tag ``food_brands`` maps to
    ``classification.brands_get_v1``). So we yield several stripped forms:
    the verbatim id, the tag-stripped id, and every progressively shorter
    underscore-prefix removal.
    """
    parts = op_id.split("_")
    cands: set[str] = {op_id}
    if op_id.startswith(tag + "_"):
        cands.add(op_id[len(tag) + 1 :])
    for i in range(1, len(parts)):
        cand = "_".join(parts[i:])
        if cand:
            cands.add(cand)
    return sorted(cands, key=lambda c: (-len(c), c))


def _resolve_namespaced(
    op_id: str,
    tag: str,
    methods: dict[str, set[str]],
    classes: dict[str, type],
) -> Optional[tuple[str, str, str, str]]:
    """Return ``(resource_attr, method_name, dotted_target, accessor)`` or None."""
    if op_id in _OP_OVERRIDES:
        res, name = _OP_OVERRIDES[op_id]
        cls = classes.get(res)
        if cls is not None and name in methods.get(res, set()):
            target = f"{cls.__module__}.{cls.__qualname__}.{name}"
            return res, name, target, f"Fatsecret.{res}.{name}()"
    candidates = _TAG_TO_RESOURCES.get(tag, list(methods.keys()))
    for res in candidates:
        cls = classes.get(res)
        if cls is None:
            continue
        for name in _candidate_method_names(op_id, tag):
            if name in methods[res]:
                target = f"{cls.__module__}.{cls.__qualname__}.{name}"
                return res, name, target, f"Fatsecret.{res}.{name}()"
    return None


def _resolve_flat(
    op_id: str,
    cls,
    flat: set[str],
) -> Optional[tuple[str, str, str]]:
    """Return ``(method_name, dotted_target, accessor)`` or None.

    For the flat (v1.0 - v1.5) shape, operationIds map directly to
    ``Fatsecret`` methods (e.g. ``foods_search_v5`` is ``Fatsecret.foods_search_v5``).
    Older tags may not yet have the ``_v1`` suffix, so we also try the
    suffix-stripped form (e.g. ``food_get_v1`` falls back to ``food_get``).
    """
    cands = [op_id]
    if op_id.endswith("_v1"):
        cands.append(op_id[: -len("_v1")])
    for name in cands:
        if name in flat:
            target = f"{cls.__module__}.{cls.__qualname__}.{name}"
            return name, target, f"Fatsecret.{name}()"
    return None


class FatsecretApiGroupsDirective(Directive):
    has_content = False
    required_arguments = 0
    optional_arguments = 0

    def run(self):
        env = self.state.document.settings.env
        spec = _load_spec(Path(env.srcdir) / "api-spec" / "openapi.generated.yaml")
        try:
            from fatsecret import Fatsecret  # type: ignore
        except Exception:
            return self._fallback()
        if spec is None:
            return self._fallback()

        methods, classes = _resource_inventory(Fatsecret)
        groups = _collect_ops(spec)
        flat_mode = not methods
        flat_set = _flat_methods(Fatsecret) if flat_mode else set()

        tag_order = sorted(groups.keys())
        if "Authentication" in tag_order:
            tag_order.remove("Authentication")
            tag_order.insert(0, "Authentication")

        lines: list[str] = []
        unresolved: list[str] = []
        seen: set[str] = set()
        flat_documented: set[str] = set()

        for tag in tag_order:
            heading = _TAG_HEADING.get(tag, tag)
            lines.append(heading)
            lines.append("-" * len(heading))
            lines.append("")
            for op_id in sorted(set(groups[tag])):
                if flat_mode:
                    resolved_f = _resolve_flat(op_id, Fatsecret, flat_set)
                    if resolved_f is None:
                        unresolved.append(f"{tag}:{op_id}")
                        lines.append(f"* ``{op_id}`` (no matching Python method)")
                        lines.append("")
                        continue
                    mname, target, accessor = resolved_f
                    flat_documented.add(mname)
                    if target in seen:
                        lines.append(f"* ``{accessor}`` -- also tagged ``{tag}``.")
                        lines.append("")
                        continue
                    seen.add(target)
                    lines.append(f"**{accessor}**")
                    lines.append("")
                    lines.append(f".. automethod:: {target}")
                    lines.append("")
                else:
                    resolved = _resolve_namespaced(op_id, tag, methods, classes)
                    if resolved is None:
                        unresolved.append(f"{tag}:{op_id}")
                        lines.append(f"* ``{op_id}`` (no matching Python method)")
                        lines.append("")
                        continue
                    attr, mname, target, accessor = resolved
                    if target in seen:
                        lines.append(f"* ``{accessor}`` -- also tagged ``{tag}``.")
                        lines.append("")
                        continue
                    seen.add(target)
                    lines.append(f"**{accessor}**")
                    lines.append("")
                    lines.append(f".. automethod:: {target}")
                    lines.append("")

        # Client utilities: everything else public on the class.
        if flat_mode:
            try:
                util = sorted(
                    m for m in flat_set
                    if m not in flat_documented
                )
            except Exception:
                util = []
        else:
            try:
                util = sorted(
                    m for m in dir(Fatsecret)
                    if not m.startswith("_")
                    and callable(getattr(Fatsecret, m, None))
                    and m not in methods
                )
            except Exception:
                util = []
        util_heading = "Client utilities"
        lines.append(util_heading)
        lines.append("-" * len(util_heading))
        lines.append("")
        for m in util:
            lines.append(f".. automethod:: fatsecret.Fatsecret.{m}")
            lines.append("")

        if unresolved:
            _log.info(
                "fatsecret_oas: %d operations had no Python match: %s%s",
                len(unresolved),
                ", ".join(unresolved[:5]),
                "..." if len(unresolved) > 5 else "",
            )

        rst = StringList(lines, source="<fatsecret_oas>")
        node = nodes.section()
        node.document = self.state.document
        self.state.nested_parse(rst, 0, node, match_titles=True)
        return node.children

    def _fallback(self):
        rst = StringList(
            [
                ".. autoclass:: fatsecret.Fatsecret",
                "   :members:",
                "   :noindex:",
                "   :exclude-members: __init__",
            ],
            source="<fatsecret_oas-fallback>",
        )
        node = nodes.section()
        node.document = self.state.document
        self.state.nested_parse(rst, 0, node, match_titles=True)
        return node.children


def setup(app):
    app.add_directive("fatsecret-api-groups", FatsecretApiGroupsDirective)
    return {"version": "1.0", "parallel_read_safe": True}
