"""Emit Pydantic v2 response models from the FatSecret XSD.

Phase 1 scope: ``foods`` resource only. The pipeline reads the cached
XSD via :mod:`xsd`, builds a graph of XSD complexTypes that compose the
``food`` / ``food_entry`` / ``serving`` family, and writes one Pydantic
class per type to ``src/fatsecret/models/_generated/<resource>.py``.

Determinism
-----------
Class order is topological with alphabetical tiebreak. Field order is
the XSD declaration order (which is the wire order). Same XSD bytes →
same Python bytes. ``oas-regen-check`` will police this.

Type mapping
------------
``xsd:long``/``xsd:int``/``xsd:integer``/``xsd:positiveInteger`` → ``int``
``xsd:decimal`` → ``Decimal``
``xsd:double``/``xsd:float`` → ``float``
``xsd:string``/``xsd:anyURI`` → ``str``
``xsd:boolean`` → ``bool``
``xsd:dateTime`` → ``datetime``
``xsd:date`` → ``date``
custom enum simpleType → ``Literal[...]``
``Ternary`` → re-exported alias from ``_common``
``food_type`` → ``FoodType`` alias from ``_common``
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

from .config import REPO_ROOT
from .xsd import XSD_NS, fetch_xsd

log = logging.getLogger(__name__)


GEN_DIR = REPO_ROOT / "src" / "fatsecret" / "models" / "_generated"


# XSD primitive → Python annotation. Anything not listed falls through
# to ``str`` with a warning so the codegen never silently produces
# ``Any``-like fields.
_XSD_PRIMITIVE_MAP: dict[str, str] = {
    "xsd:long": "int",
    "xsd:int": "int",
    "xsd:integer": "int",
    "xsd:positiveInteger": "int",
    "xsd:short": "int",
    "xsd:decimal": "Decimal",
    "xsd:double": "float",
    "xsd:float": "float",
    "xsd:string": "str",
    "xsd:anyURI": "str",
    "xsd:boolean": "bool",
    "xsd:dateTime": "datetime",
    "xsd:date": "date",
}


# Aliases re-used from ``_common``. Keys are XSD simpleType names.
_COMMON_ALIASES: dict[str, str] = {
    "Ternary": "Ternary",
    "food_type": "FoodType",
}


# Foods-resource seed types. Anything reachable from these (via complexType
# composition) is emitted into ``_generated/foods.py``.
_FOODS_SEED_TYPES: tuple[str, ...] = (
    "food",
    "food_entry",
    "serving",
    "food_image",
    "food_images",
    "food_attributes",
    "food_sub_categories",
    "food_sub_category",
    "allergens",
    "allergen",
    "preferences",
    "preference",
)

# Foods-resource seed elements (top-level wrappers backed by anonymous
# complexTypes). Each is materialised as its own model class named after
# the element.
_FOODS_SEED_ELEMENTS: tuple[str, ...] = (
    "foods",
    "foods_search",
    "food_results",
    "food_entries",
)


# ---------------------------------------------------------------------------
# XSD parsing
# ---------------------------------------------------------------------------


def _snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_") if part)


def _load_root() -> ET.Element:
    body = fetch_xsd()
    return ET.fromstring(body)


def _index_simple_types(root: ET.Element) -> dict[str, ET.Element]:
    return {
        s.get("name"): s for s in root.findall(XSD_NS + "simpleType") if s.get("name")
    }


def _index_complex_types(root: ET.Element) -> dict[str, ET.Element]:
    return {
        c.get("name"): c for c in root.findall(XSD_NS + "complexType") if c.get("name")
    }


def _index_elements(root: ET.Element) -> dict[str, ET.Element]:
    return {e.get("name"): e for e in root.findall(XSD_NS + "element") if e.get("name")}


def _resolve_simple_base(name: str, simple_types: dict[str, ET.Element]) -> str | None:
    """Return the ``xsd:*`` primitive a simpleType ultimately restricts.

    Walks one chain of ``<restriction base=...>`` references. Returns
    ``None`` if the name is not a known simpleType.
    """
    seen: set[str] = set()
    current = name
    while current and current not in seen:
        seen.add(current)
        if current.startswith("xsd:"):
            return current
        elem = simple_types.get(current)
        if elem is None:
            return None
        restriction = elem.find(XSD_NS + "restriction")
        if restriction is None:
            return None
        base = restriction.get("base")
        if base is None:
            return None
        current = base
    return None


def _enum_values(name: str, simple_types: dict[str, ET.Element]) -> list[str] | None:
    """Return enumeration string values for a simpleType, or ``None`` if it
    has no enumeration restriction.
    """
    elem = simple_types.get(name)
    if elem is None:
        return None
    restriction = elem.find(XSD_NS + "restriction")
    if restriction is None:
        return None
    values = [
        e.get("value")
        for e in restriction.findall(XSD_NS + "enumeration")
        if e.get("value") is not None
    ]
    return values or None


# ---------------------------------------------------------------------------
# Field model
# ---------------------------------------------------------------------------


class _FieldSpec:
    """A single emitted field on a class."""

    __slots__ = (
        "name",
        "annotation",
        "optional",
        "is_list",
        "imports",
        "common_aliases",
    )

    def __init__(
        self,
        name: str,
        annotation: str,
        optional: bool,
        is_list: bool,
        imports: set[str],
        common_aliases: set[str],
    ) -> None:
        self.name = name
        self.annotation = annotation
        self.optional = optional
        self.is_list = is_list
        self.imports = imports
        self.common_aliases = common_aliases


class _ClassSpec:
    """A single emitted class."""

    __slots__ = ("name", "source_xsd", "fields", "depends_on")

    def __init__(self, name: str, source_xsd: str) -> None:
        self.name = name
        self.source_xsd = source_xsd
        self.fields: list[_FieldSpec] = []
        # Class names this class references (for topological ordering).
        self.depends_on: set[str] = set()


# ---------------------------------------------------------------------------
# Type resolution for an <xsd:element> child
# ---------------------------------------------------------------------------


def _resolve_field_type(
    type_name: str | None,
    inline_complex: ET.Element | None,
    simple_types: dict[str, ET.Element],
    complex_types: dict[str, ET.Element],
    pending_inline: list[tuple[str, ET.Element]],
    parent_name: str,
    field_name: str,
) -> tuple[str, set[str], set[str], set[str]]:
    """Return ``(annotation, imports, common_aliases, class_deps)`` for one
    XSD element child.

    ``imports`` collects ``"Decimal"``, ``"datetime"``, ``"Literal"`` etc.
    that need to land in the module preamble. ``common_aliases`` collects
    names imported from ``.._common``. ``class_deps`` collects sibling
    class names referenced by this field (drives topological ordering).

    Anonymous inline complexTypes are queued onto ``pending_inline`` and
    referenced by a synthesised PascalCase class name derived from the
    parent class + field name (e.g. ``food.servings`` → ``FoodServings``).
    """
    imports: set[str] = set()
    aliases: set[str] = set()
    deps: set[str] = set()

    # 1) Inline anonymous complexType.
    if inline_complex is not None:
        # ``parent_name`` may be a snake_case XSD type name (``food``) or a
        # PascalCase synthesised class name (``RecipesRecipe``); only convert
        # when it looks snake_case.
        if any(c.isupper() for c in parent_name) and "_" not in parent_name:
            parent_pascal = parent_name
        else:
            parent_pascal = _snake_to_pascal(parent_name)
        synth_name = parent_pascal + _snake_to_pascal(field_name)
        pending_inline.append((synth_name, inline_complex))
        deps.add(synth_name)
        return synth_name, imports, aliases, deps

    if type_name is None:
        # Should not happen in a well-formed XSD; fall back to ``str``.
        log.warning(
            "element %s/%s has no type and no inline complex", parent_name, field_name
        )
        return "str", imports, aliases, deps

    # 2) Common alias (Ternary, FoodType).
    if type_name in _COMMON_ALIASES:
        alias = _COMMON_ALIASES[type_name]
        aliases.add(alias)
        return alias, imports, aliases, deps

    # ``xsd:Ternary`` shows up once in the XSD as a typo for ``Ternary``.
    if type_name == "xsd:Ternary":
        aliases.add("Ternary")
        return "Ternary", imports, aliases, deps

    # 3) Custom enum simpleType → Literal[...].
    enum_vals = _enum_values(type_name, simple_types)
    if enum_vals is not None:
        imports.add("Literal")
        rendered = ", ".join(repr(v) for v in enum_vals)
        return f"Literal[{rendered}]", imports, aliases, deps

    # 4) Custom (non-enum) simpleType → resolve to its primitive base.
    if type_name in simple_types:
        base = _resolve_simple_base(type_name, simple_types)
        if base is not None and base in _XSD_PRIMITIVE_MAP:
            py = _XSD_PRIMITIVE_MAP[base]
            if py == "Decimal":
                imports.add("Decimal")
            elif py == "datetime":
                imports.add("datetime")
            elif py == "date":
                imports.add("date")
            return py, imports, aliases, deps

    # 5) XSD primitive directly.
    if type_name in _XSD_PRIMITIVE_MAP:
        py = _XSD_PRIMITIVE_MAP[type_name]
        if py == "Decimal":
            imports.add("Decimal")
        elif py == "datetime":
            imports.add("datetime")
        elif py == "date":
            imports.add("date")
        return py, imports, aliases, deps

    # 6) Reference to another named complexType.
    if type_name in complex_types:
        # Special-case: ``food_sub_category`` is a degenerate complexType
        # that restricts xsd:string. Treat as ``str``.
        ctype = complex_types[type_name]
        if ctype.find(XSD_NS + "sequence") is None:
            restriction = ctype.find(XSD_NS + "restriction")
            if (
                restriction is not None
                and restriction.get("base") in _XSD_PRIMITIVE_MAP
            ):
                return (
                    _XSD_PRIMITIVE_MAP[restriction.get("base")],
                    imports,
                    aliases,
                    deps,
                )
        cls = _snake_to_pascal(type_name)
        deps.add(cls)
        return cls, imports, aliases, deps

    # 7) Unknown — log and fall back to str.
    log.warning(
        "unresolved type %r at %s/%s; using str", type_name, parent_name, field_name
    )
    return "str", imports, aliases, deps


def _build_class_from_complex(
    class_name: str,
    source_xsd: str,
    ctype: ET.Element,
    simple_types: dict[str, ET.Element],
    complex_types: dict[str, ET.Element],
    pending_inline: list[tuple[str, ET.Element]],
) -> _ClassSpec:
    spec = _ClassSpec(class_name, source_xsd)
    seq = ctype.find(XSD_NS + "sequence")
    if seq is None:
        return spec
    for elem in seq.findall(XSD_NS + "element"):
        name = elem.get("name")
        if name is None:
            continue
        type_name = elem.get("type")
        inline = elem.find(XSD_NS + "complexType")
        max_occ = elem.get("maxOccurs", "1")
        is_list = max_occ == "unbounded" or (max_occ.isdigit() and int(max_occ) > 1)
        # Force every element field to Optional with default=None. The XSD's
        # "required" claim does not match FatSecret's live behaviour
        # (e.g. `serving.is_default` is declared required but the live API
        # often omits it). Tolerating drift here matches the `extra="allow"`
        # philosophy on `_FS_Base` — accept real responses rather than
        # raise ValidationError on a field FatSecret silently dropped.
        optional = True

        annotation, imports, aliases, deps = _resolve_field_type(
            type_name,
            inline,
            simple_types,
            complex_types,
            pending_inline,
            class_name,
            name,
        )
        spec.fields.append(
            _FieldSpec(
                name=name,
                annotation=annotation,
                optional=optional,
                is_list=is_list,
                imports=imports,
                common_aliases=aliases,
            )
        )
        spec.depends_on.update(deps)
    return spec


# ---------------------------------------------------------------------------
# Resource assembly
# ---------------------------------------------------------------------------


def _gather_classes(
    seed_types: tuple[str, ...],
    seed_elements: tuple[str, ...],
) -> list[_ClassSpec]:
    """Generic seed-driven class gathering.

    ``seed_types`` are XSD ``complexType`` names; ``seed_elements`` are
    top-level ``element`` names whose body is an anonymous complexType.
    Reachable inline complexTypes get walked into synthesised classes
    (e.g. ``food.servings`` -> ``FoodServings``).
    """
    root = _load_root()
    simple_types = _index_simple_types(root)
    complex_types = _index_complex_types(root)
    elements = _index_elements(root)

    classes: dict[str, _ClassSpec] = {}
    pending_inline: list[tuple[str, ET.Element]] = []

    for type_name in seed_types:
        ctype = complex_types.get(type_name)
        if ctype is None:
            continue
        if ctype.find(XSD_NS + "sequence") is None:
            continue
        class_name = _snake_to_pascal(type_name)
        if class_name in classes:
            continue
        classes[class_name] = _build_class_from_complex(
            class_name, type_name, ctype, simple_types, complex_types, pending_inline
        )

    for elem_name in seed_elements:
        elem = elements.get(elem_name)
        if elem is None:
            continue
        inline = elem.find(XSD_NS + "complexType")
        if inline is None:
            continue
        class_name = _snake_to_pascal(elem_name)
        if class_name in classes:
            continue
        classes[class_name] = _build_class_from_complex(
            class_name, elem_name, inline, simple_types, complex_types, pending_inline
        )

    while pending_inline:
        synth_name, inline_ct = pending_inline.pop(0)
        if synth_name in classes:
            continue
        classes[synth_name] = _build_class_from_complex(
            synth_name,
            f"<inline {synth_name}>",
            inline_ct,
            simple_types,
            complex_types,
            pending_inline,
        )

    return _topo_sort(classes)


def _gather_foods_classes() -> list[_ClassSpec]:
    """Return the ordered list of class specs for the foods resource."""
    return _gather_classes(_FOODS_SEED_TYPES, _FOODS_SEED_ELEMENTS)


# ---------------------------------------------------------------------------
# Seed tables for the remaining Phase 2 resources
# ---------------------------------------------------------------------------


# Recipes: the ``recipes`` element wraps an anonymous complexType that
# itself contains an anonymous ``recipe`` complexType. Both surface as
# generated classes (``Recipes`` and ``RecipesRecipe``); we re-export the
# latter under the friendlier ``Recipe`` name in models/__init__.py.
_RECIPES_SEED_TYPES: tuple[str, ...] = ()
_RECIPES_SEED_ELEMENTS: tuple[str, ...] = ("recipes",)


# Profile (auth + plain): the ``profile`` element holds an anonymous
# complexType whose fields are simpleType-restricted scalars. Same shape
# is returned by ``profile.create``, ``profile.get``, ``profile.get_auth``.
_PROFILE_SEED_TYPES: tuple[str, ...] = ()
_PROFILE_SEED_ELEMENTS: tuple[str, ...] = ("profile",)


# Exercise Diary: ``exercise_entries``, ``exercise_types``, ``month``.
# ``exercise``, ``exercise_entry``, and ``day`` are named complexTypes
# referenced from those elements.
_EXERCISES_SEED_TYPES: tuple[str, ...] = (
    "exercise",
    "exercise_entry",
    "day",
)
_EXERCISES_SEED_ELEMENTS: tuple[str, ...] = (
    "exercise_entries",
    "exercise_types",
    "month",
)


# Food Diary: reuses ``food_entry``/``food_entries`` plus the ``month``
# / ``day`` shape shared with the other diaries.
_FOOD_DIARY_SEED_TYPES: tuple[str, ...] = (
    "food_entry",
    "day",
)
_FOOD_DIARY_SEED_ELEMENTS: tuple[str, ...] = (
    "food_entries",
    "month",
)


# Weight Diary: only ``weights.get_month`` is XSD-covered (via the shared
# ``month``/``day`` shape). The other weight endpoints fall back to
# returning raw ``dict`` because the XSD doesn't model them.
_WEIGHT_DIARY_SEED_TYPES: tuple[str, ...] = ("day",)
_WEIGHT_DIARY_SEED_ELEMENTS: tuple[str, ...] = ("month",)


def _gather_recipes_classes() -> list[_ClassSpec]:
    return _gather_classes(_RECIPES_SEED_TYPES, _RECIPES_SEED_ELEMENTS)


def _gather_profile_classes() -> list[_ClassSpec]:
    return _gather_classes(_PROFILE_SEED_TYPES, _PROFILE_SEED_ELEMENTS)


def _gather_exercise_diary_classes() -> list[_ClassSpec]:
    return _gather_classes(_EXERCISES_SEED_TYPES, _EXERCISES_SEED_ELEMENTS)


def _gather_food_diary_classes() -> list[_ClassSpec]:
    return _gather_classes(_FOOD_DIARY_SEED_TYPES, _FOOD_DIARY_SEED_ELEMENTS)


def _gather_weight_diary_classes() -> list[_ClassSpec]:
    return _gather_classes(_WEIGHT_DIARY_SEED_TYPES, _WEIGHT_DIARY_SEED_ELEMENTS)


def _topo_sort(classes: dict[str, _ClassSpec]) -> list[_ClassSpec]:
    remaining = dict(classes)
    ordered: list[_ClassSpec] = []
    placed: set[str] = set()
    while remaining:
        ready = sorted(
            name
            for name, spec in remaining.items()
            if all(dep not in remaining for dep in spec.depends_on)
        )
        if not ready:
            # Cycle — give up on topology, place the rest alphabetically and
            # rely on Pydantic v2 forward-ref resolution.
            for name in sorted(remaining):
                ordered.append(remaining[name])
                placed.add(name)
            break
        for name in ready:
            ordered.append(remaining.pop(name))
            placed.add(name)
    return ordered


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


_HEADER = (
    "# AUTO-GENERATED by scripts/oas-sync emit-models {resource}. "
    "Do not edit by hand.\n"
    '"""Pydantic response models for the FatSecret ``{resource}`` resource '
    '(generated from XSD)."""\n\n'
    "from __future__ import annotations\n\n"
)


def _render(resource: str, classes: list[_ClassSpec]) -> str:
    typing_imports: set[str] = set()
    decimal_needed = False
    datetime_needed = False
    date_needed = False
    common_aliases: set[str] = set()

    for cls in classes:
        for f in cls.fields:
            for imp in f.imports:
                if imp == "Decimal":
                    decimal_needed = True
                elif imp == "datetime":
                    datetime_needed = True
                elif imp == "date":
                    date_needed = True
                elif imp == "Literal":
                    typing_imports.add("Literal")
            common_aliases.update(f.common_aliases)
            if f.optional:
                typing_imports.add("Optional")
            if f.is_list:
                typing_imports.add("List")

    out = StringIO()
    out.write(_HEADER.format(resource=resource))

    # stdlib imports
    if decimal_needed:
        out.write("from decimal import Decimal\n")
    if datetime_needed and date_needed:
        out.write("from datetime import date, datetime\n")
    elif datetime_needed:
        out.write("from datetime import datetime\n")
    elif date_needed:
        out.write("from datetime import date\n")
    if typing_imports:
        out.write(f"from typing import {', '.join(sorted(typing_imports))}\n")
    if decimal_needed or datetime_needed or date_needed or typing_imports:
        out.write("\n")

    # third-party
    out.write("from pydantic import Field\n\n")

    # internal
    out.write("from .._common import _FS_Base")
    if common_aliases:
        for alias in sorted(common_aliases):
            out.write(f", {alias}")
    out.write("\n\n\n")

    # classes
    for i, cls in enumerate(classes):
        if i > 0:
            out.write("\n\n")
        _render_class(out, cls)

    # ensure trailing newline
    body = out.getvalue()
    if not body.endswith("\n"):
        body += "\n"
    return body


def _render_class(out: StringIO, cls: _ClassSpec) -> None:
    out.write(f"class {cls.name}(_FS_Base):\n")
    out.write(f'    """Generated from XSD ``{cls.source_xsd}``."""\n\n')
    if not cls.fields:
        out.write("    pass\n")
        return
    for f in cls.fields:
        ann = f.annotation
        if f.is_list:
            ann = f"List[{ann}]"
        if f.optional:
            ann = f"Optional[{ann}]"
            default = " = Field(default=None)"
        else:
            default = ""
        out.write(f"    {f.name}: {ann}{default}\n")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_RESOURCE_BUILDERS = {
    "foods": _gather_foods_classes,
    "recipes": _gather_recipes_classes,
    "profile_auth": _gather_profile_classes,
    "exercise_diary": _gather_exercise_diary_classes,
    "food_diary": _gather_food_diary_classes,
    "weight_diary": _gather_weight_diary_classes,
}


def emit_models(resource: str) -> Path:
    """Generate ``src/fatsecret/models/_generated/<resource>.py``.

    Returns the path written. Same XSD bytes → same Python bytes.
    """
    builder = _RESOURCE_BUILDERS.get(resource)
    if builder is None:
        raise ValueError(
            f"unknown resource {resource!r}; " f"known: {sorted(_RESOURCE_BUILDERS)}"
        )
    classes = builder()
    rendered = _render(resource, classes)
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    init = GEN_DIR / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")
    out_path = GEN_DIR / f"{resource}.py"
    out_path.write_text(rendered, encoding="utf-8")
    log.info("wrote %s (%d classes)", out_path, len(classes))
    return out_path
