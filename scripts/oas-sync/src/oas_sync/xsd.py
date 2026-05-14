"""Source FatSecret response shapes from the published XSD.

FatSecret ships an XSD that documents every legacy v1 response payload
(food, food_entry, recipe, exercise, profile, ...) with proper types.
This module fetches + caches the XSD alongside the HTML doc cache and
exposes ``derive_response_for(method)`` which returns a structural skeleton
matching the existing raw-YAML ``response:`` field.

Deliberately collapsed output
-----------------------------
The downstream consumer (``emit_resource.derive_unwrap``) walks a
*single*-non-scalar-child chain.  We reproduce the same lossy shape the
HTML-example walker has produced for years:

  * Multi-non-scalar complexTypes collapse to ``{}``.
  * Single non-scalar children survive; arrays surface as ``[{}]``.
  * Pure-scalar complexTypes collapse to ``{}``.
  * Plural-singular pairs (e.g. ``recipes`` → ``recipe``) are coerced to
    arrays even when the XSD's ``maxOccurs`` is missing — the XSD has
    well-known omissions here that the wire format contradicts.

Coverage is partial: the XSD is the v1-era schema, so v2+ additions
(e.g. ``foods_search`` v2-v5, ``food_attributes``, ``added_sugars``) and
post-v1 endpoints not modelled at all (``recipes.get_favorites``,
``saved_meals.*``, ``feedback``, native REST APIs) fall back to the HTML
example walker in ``parse.py``.

Determinism
-----------
The XSD body is cached on disk; same input → same output.  No clock,
no LLM, no random ordering.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import CACHE_DIR, REQUEST_TIMEOUT_S, USER_AGENT

log = logging.getLogger(__name__)

XSD_URL = "https://platform.fatsecret.com/api/1.0/fatsecret.xsd"
XSD_NS = "{http://www.w3.org/2001/XMLSchema}"


# ---------------------------------------------------------------------------
# Fetch + cache
# ---------------------------------------------------------------------------


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.xsd"


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=10))
def _fetch_remote(url: str, client: httpx.Client) -> str:
    resp = client.get(url, timeout=REQUEST_TIMEOUT_S, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def fetch_xsd(*, force: bool = False) -> str:
    """Fetch the XSD with on-disk cache (parallels http.fetch)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(XSD_URL)
    if path.exists() and not force:
        log.debug("xsd cache hit: %s", XSD_URL)
        return path.read_text(encoding="utf-8")
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        log.info("fetch xsd: %s", XSD_URL)
        body = _fetch_remote(XSD_URL, client)
        path.write_text(body, encoding="utf-8")
        return body


# ---------------------------------------------------------------------------
# Parse + walk
# ---------------------------------------------------------------------------


def _is_simple_type(type_name: str | None, simple_types: set[str]) -> bool:
    if type_name is None:
        return False
    if type_name.startswith("xsd:"):
        return True
    return type_name in simple_types


def _is_plural_of(plural: str, singular: str) -> bool:
    """English plural-singular pair check.  Mirrors parse._is_plural_of."""
    if not plural or not singular or plural == singular:
        return False
    if plural == singular + "s":
        return True
    if plural == singular + "es":
        return True
    if singular.endswith("y") and plural == singular[:-1] + "ies":
        return True
    return False


def _walk_complex(
    ctype: ET.Element,
    parent_key: str | None,
    complex_types: dict[str, ET.Element],
    simple_types: set[str],
) -> Any:
    """Walk a complexType, returning the collapsed structural skeleton.

    Mirrors parse._walk_response: keep only the single non-scalar child;
    multi- or pure-scalar collapses to ``{}``.
    """
    seq = ctype.find(XSD_NS + "sequence")
    # Some complexTypes wrap simple restrictions; treat as scalar leaf.
    if seq is None:
        return {}

    children: list[tuple[str, str | None, ET.Element | None, bool]] = []
    for elem in seq.findall(XSD_NS + "element"):
        name = elem.get("name")
        if name is None:
            continue
        type_name = elem.get("type")
        max_occ = elem.get("maxOccurs", "1")
        is_array = max_occ == "unbounded" or (
            max_occ.isdigit() and int(max_occ) > 1
        )
        inline_complex = elem.find(XSD_NS + "complexType")
        children.append((name, type_name, inline_complex, is_array))

    non_scalars: list[tuple[str, str | None, ET.Element | None, bool]] = []
    for name, type_name, inline, is_array in children:
        if inline is not None:
            non_scalars.append((name, type_name, inline, is_array))
        elif type_name and not _is_simple_type(type_name, simple_types):
            non_scalars.append((name, type_name, inline, is_array))
        elif is_array:
            # Array of scalars — still a non-scalar branch in skeleton terms.
            non_scalars.append((name, type_name, inline, is_array))

    if not non_scalars:
        return {}
    if len(non_scalars) > 1:
        return {}

    name, type_name, inline, is_array = non_scalars[0]
    sub: Any
    if inline is not None:
        sub = _walk_complex(inline, name, complex_types, simple_types)
    elif type_name and not _is_simple_type(type_name, simple_types):
        target = complex_types.get(type_name)
        sub = _walk_complex(target, name, complex_types, simple_types) if target is not None else {}
    else:
        sub = {}

    # Plural-singular coercion: even when XSD lacks maxOccurs="unbounded"
    # (the FatSecret XSD has known omissions, e.g. <recipes><recipe>...</recipes>),
    # if the parent name is the plural of this child name, the wire format is
    # an array.  Promote.
    if (
        not is_array
        and parent_key is not None
        and _is_plural_of(parent_key, name)
    ):
        is_array = True

    if is_array:
        return {name: [{}]}
    return {name: sub}


def _walk_element(
    elem: ET.Element,
    complex_types: dict[str, ET.Element],
    simple_types: set[str],
) -> Any:
    """Walk a top-level <xsd:element>, returning its inner skeleton."""
    type_name = elem.get("type")
    inline = elem.find(XSD_NS + "complexType")
    name = elem.get("name")
    if inline is not None:
        return _walk_complex(inline, name, complex_types, simple_types)
    if type_name and not _is_simple_type(type_name, simple_types):
        target = complex_types.get(type_name)
        if target is None:
            return {}
        return _walk_complex(target, name, complex_types, simple_types)
    # Scalar top-level element (e.g. <element name="success" type="xsd:boolean"/>)
    return None


@lru_cache(maxsize=1)
def load_schema(force_fetch: bool = False) -> dict[str, Any]:
    """Return ``{element_name: walked_inner_skeleton}`` for every top-level
    XSD element that resolves to a complexType.

    Scalar top-level elements (e.g. ``success``) are excluded from the
    mapping — they have no inner shape.
    """
    body = fetch_xsd(force=force_fetch)
    root = ET.fromstring(body)
    simple_types: set[str] = {
        s.get("name") for s in root.findall(XSD_NS + "simpleType") if s.get("name")
    }
    complex_types: dict[str, ET.Element] = {
        c.get("name"): c
        for c in root.findall(XSD_NS + "complexType")
        if c.get("name")
    }
    out: dict[str, Any] = {}
    for elem in root.findall(XSD_NS + "element"):
        name = elem.get("name")
        if not name:
            continue
        inner = _walk_element(elem, complex_types, simple_types)
        if inner is None:
            continue
        out[name] = inner
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Method → element mapping
# ---------------------------------------------------------------------------


# Method-name (without ``.vN`` suffix) → XSD top-level element name.
# Built explicitly so coverage is auditable and so we never silently match
# the wrong element.  Methods absent from this table fall back to the HTML
# example walker in parse.py.
_METHOD_TO_ELEMENT: dict[str, str] = {
    "food.get": "food",
    "foods.search": "foods",  # v1; v2+ overridden below
    "food_entries.get": "food_entries",
    "food_entries.get_month": "month",
    "weights.get_month": "month",
    "exercise_entries.get_month": "month",
    "exercises.get": "exercise_types",
    "exercise_entries.get": "exercise_entries",
    "profile.get": "profile",
    "profile.get_auth": "profile",
    "profile.create": "profile",
    "recipes.search": "recipes",
}

# (method, version) overrides where the version-specific root differs.
_METHOD_VERSION_TO_ELEMENT: dict[tuple[str, str], str] = {
    ("foods.search", "v2"): "foods_search",
    ("foods.search", "v3"): "foods_search",
    ("foods.search", "v4"): "foods_search",
    ("foods.search", "v5"): "foods_search",
}


def derive_response_for(method: str, version: str) -> dict[str, Any] | None:
    """Return the structural skeleton for ``(method, version)`` from the XSD,
    or ``None`` if the XSD does not cover this endpoint.
    """
    schema = load_schema()
    elem_name = _METHOD_VERSION_TO_ELEMENT.get((method, version))
    if elem_name is None:
        elem_name = _METHOD_TO_ELEMENT.get(method)
    if elem_name is None:
        return None
    inner = schema.get(elem_name)
    if inner is None:
        return None
    # Deep-copy so callers (and the YAML dumper) never see shared references.
    return {elem_name: copy.deepcopy(inner)}
