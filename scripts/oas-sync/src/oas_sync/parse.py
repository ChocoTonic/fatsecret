"""Parse a single FatSecret method-doc HTML page into an EndpointSpec.

Extracts everything codegen needs straight from the docs HTML — parameters,
HTTP verb, REST URL (for native APIs), and the response shape derived from
the page's "Example Response" JSON block.  No hand-written code is consulted.

The extracted shape is intentionally lossy: only the structural skeleton
that drives codegen's `derive_unwrap` walk is preserved.  Specifically:

  * ``{success: {value: <scalar>}}`` is canonicalised to ``{success: 1}``
    (mutator marker so generated code returns a bool).
  * ``{<key>: {value: <scalar>}}`` collapses to ``{<key>: ""}`` (ID-return
    pattern; generated code unwraps the scalar).
  * The walker follows single-non-scalar-child chains.  Plural-singular
    pairs (e.g. ``food_entries -> food_entry``) yield ``{singular: [{}]}``
    even when the docs example flattens the singleton list to a dict.
  * Multi-non-scalar dicts and pure-scalar dicts collapse to ``{}``.

Determinism: same HTML in -> same Python dict out.  No timestamps, no
random ordering, no LLM.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from selectolax.parser import HTMLParser, Node

from .models import EndpointSpec, MethodRef, Parameter
from .xsd import derive_response_for as _xsd_response_for

log = logging.getLogger(__name__)


DEPRECATION_PATTERNS = (
    "this is version has been deprecated",
    "this version has been deprecated",
    "deprecated",  # last-resort match; we still gate on banner-style nodes
)

# Parameter names dropped before output. ``format`` is universally optional and
# never set by callers; ``method`` is added back by the assembler from the
# operation's ``api_method_param`` field.
_PARAM_NAME_DROP = {"format", "method", ""}

# Parameter names that the docs misdocument as Required even though the wire
# API tolerates omission (it falls back to the current day for ``date``-style
# params, etc.).  We force these to Optional so callers can omit them.
_FORCE_OPTIONAL_NAMES = {"date", "brand_type"}

# Per-endpoint Optional-promotion table.  The docs mark these as Required but
# the FatSecret API tolerates omission and the existing test suite calls the
# methods without them.  Keyed by ``(method, version)`` -> {param names}.
_FORCE_OPTIONAL_PER_ENDPOINT: dict[tuple[str, str], frozenset[str]] = {
    ("food_entries.get", "v1"): frozenset({"food_entry_id"}),
    ("food_entries.get", "v2"): frozenset({"food_entry_id"}),
}

# Native REST endpoints that are POST-with-JSON-body rather than the legacy
# ``method=`` query-string style.  These are the only endpoints for which the
# raw YAML carries a ``rest_url``; everything else stays method-style and the
# field is left null so the assembler synthesises ``/rest/server.api``.
_NATIVE_REST_URLS: dict[tuple[str, str], str] = {
    ("natural.language.processing", "v1"): (
        "https://platform.fatsecret.com/rest/natural-language-processing/v1"
    ),
    ("image.recognition", "v1"): (
        "https://platform.fatsecret.com/rest/image-recognition/v1"
    ),
    ("image.recognition", "v2"): (
        "https://platform.fatsecret.com/rest/image-recognition/v2"
    ),
    ("feedback", "v1"): "https://platform.fatsecret.com/rest/feedback/v1",
}


# Section-heading patterns inside the docs body.  Selectolax doesn't give us a
# stable DOM-walk API, so we slice the raw HTML between known h5/h6 anchors and
# then re-parse the slice.  Cheaper than a full traversal and produces the same
# result every run.
_RE_PARAMS_HEADING = re.compile(r"<h\d[^>]*>\s*Parameters\s*</h\d>", re.IGNORECASE)
_RE_RESPONSE_HEADING = re.compile(r"<h\d[^>]*>\s*Response\s*</h\d>", re.IGNORECASE)
_RE_EXAMPLE_HEADING = re.compile(
    r"<h\d[^>]*>\s*Example\s+Response[^<]*</h\d>", re.IGNORECASE
)
_RE_ERRORS_HEADING = re.compile(r"<h\d[^>]*>\s*Error\s+Codes\s*</h\d>", re.IGNORECASE)
_RE_HTTP_VERB = re.compile(
    r"HTTP\s*[\'\"]?(GET|POST|PUT|DELETE|PATCH)[\'\"]?",
    re.IGNORECASE,
)


def _text(node: Node | None) -> str:
    return (node.text() if node else "").strip()


# ---------------------------------------------------------------------------
# Top-level page metadata
# ---------------------------------------------------------------------------


def _extract_description(tree: HTMLParser) -> str:
    """Pull the operation-level prose from the docs page.

    The FatSecret docs put the prose under ``<div class="doc__description">``
    with an internal ``<h5>Description</h5>`` heading followed by one or more
    ``<p>`` elements.  After the prose come nested ``<div>`` blocks with
    sub-headings such as "Why are we introducing this version?" / "Updates
    to food labels"; we skip those and surface only the leading paragraph(s)
    so the generated docstring stays focused on what the endpoint *does*.

    Returns ``""`` when the description block is absent — callers preserve
    the existing empty-``notes`` behavior in that case.
    """
    desc = tree.css_first("div.doc__description")
    if desc is None:
        return ""
    paragraphs: list[str] = []
    for child in desc.iter(include_text=False):
        if child.tag in ("h5", "h6"):
            continue
        if child.tag == "p":
            text = " ".join((child.text() or "").split())
            if text:
                paragraphs.append(text)
        elif child.tag == "div":
            # First nested div ends the leading prose; everything after is
            # version-history / change-notes that doesn't belong in a method
            # docstring.
            break
    return " ".join(paragraphs).strip()


def _detect_deprecated(tree: HTMLParser) -> bool:
    for node in tree.css("[class*='deprecat'], [class*='warning'], [class*='banner']"):
        if "deprecat" in (node.text() or "").lower():
            return True
    for node in tree.css("h1, h2, h3, p"):
        txt = (node.text() or "").lower()
        for pat in DEPRECATION_PATTERNS[:-1]:
            if pat in txt:
                return True
    return False


def _detect_premier(tree: HTMLParser) -> bool:
    body = tree.body.text() if tree.body else ""
    body_l = body.lower()
    return "premier" in body_l and (
        "premier exclusive" in body_l or "* premier" in body_l
    )


def _detect_http_verb(html: str) -> str:
    m = _RE_HTTP_VERB.search(html)
    return m.group(1).upper() if m else "GET"


def _detect_oauth(tree: HTMLParser) -> list[str]:
    body_text = (tree.body.text() if tree.body else "").lower()
    flows: list[str] = []
    if "oauth 1" in body_text or "oauth1" in body_text or "hmac-sha1" in body_text:
        flows.append("oauth1")
    if "oauth 2" in body_text or "oauth2" in body_text or "bearer" in body_text:
        flows.append("oauth2")
    return flows or ["oauth1"]


def _detect_scope(tree: HTMLParser) -> str:
    body_text = (tree.body.text() if tree.body else "").lower()
    for candidate in (
        "premier",
        "barcode",
        "nlp",
        "image-recognition",
        "feedback",
        "localization",
    ):
        if f"scope: {candidate}" in body_text or f'"{candidate}"' in body_text:
            return candidate
    return "basic"


# ---------------------------------------------------------------------------
# Section slicing
# ---------------------------------------------------------------------------


def _section(
    html: str, start_re: re.Pattern[str], end_re: re.Pattern[str]
) -> str | None:
    m1 = start_re.search(html)
    if m1 is None:
        return None
    m2 = end_re.search(html, m1.end())
    end = m2.start() if m2 else len(html)
    return html[m1.end() : end]


def _body_html(tree: HTMLParser, raw_html: str) -> str:
    if tree.body is not None:
        return tree.body.html or raw_html
    return raw_html


# ---------------------------------------------------------------------------
# Parameter table extraction
# ---------------------------------------------------------------------------


def _row_cells(row: Node) -> tuple[list[Node], list[Node]]:
    """Return (th_cells, td_cells) preserving document order within each list."""
    ths = row.css("th")
    tds = row.css("td")
    return ths, tds


def _parse_parameter_row(
    row: Node, extra_force_optional: frozenset[str] = frozenset()
) -> Parameter | None:
    ths, tds = _row_cells(row)
    if len(ths) != 1 or len(tds) < 3:
        return None
    name = (ths[0].text() or "").strip()
    if name.lower() in _PARAM_NAME_DROP:
        return None
    # The 'URL / Method' subtable mirrors the parameter-table schema but its
    # rows describe endpoint dispatch (e.g. "URL (new) Method" / "method") not
    # callable parameters; identify them by a multi-word name with whitespace
    # or a non-identifier-safe character.
    if " " in name or "/" in name or "(" in name:
        return None
    type_ = (tds[0].text() or "").strip() or None
    if type_ and type_.upper() == "N/A":
        return None
    required_raw = (tds[1].text() or "").strip().lower()
    required = required_raw == "required"
    if name in _FORCE_OPTIONAL_NAMES or name in extra_force_optional:
        required = False
    description = (tds[2].text() or "").strip()
    return Parameter(
        name=name,
        type=type_,
        required=required,
        description=description,
    )


def _is_params_header_row(row: Node) -> bool:
    """Header row marker: cells read NAME, TYPE, REQUIRED, DESCRIPTION."""
    header_cells = [c.text().strip().upper() for c in row.css("th, td")]
    if not header_cells or header_cells[0] != "NAME":
        return False
    expected = {"NAME", "TYPE", "REQUIRED", "DESCRIPTION"}
    return expected.issubset(set(header_cells))


def _parse_parameters(
    html: str, extra_force_optional: frozenset[str] = frozenset()
) -> list[Parameter]:
    """Pull every (name, type, required, description) row from the
    'Additional Parameters' / 'Json Property Descriptions' subtable beneath
    the Parameters heading.

    The Parameters section typically has two tables: a leading 'URL / Method'
    table that documents endpoint dispatch (its rows describe URL patterns,
    not callable parameters) and a trailing 'Additional Parameters' table
    that lists the real parameters.  We walk every table whose header is
    NAME|TYPE|REQUIRED|DESCRIPTION and append any row whose first cell is a
    proper parameter name (not 'URL (new) Method' / 'N/A').
    """
    section = _section(html, _RE_PARAMS_HEADING, _RE_RESPONSE_HEADING)
    if section is None:
        return []
    sub = HTMLParser(section)
    out: list[Parameter] = []
    for table in sub.css("table"):
        rows = table.css("tr")
        if not rows or not _is_params_header_row(rows[0]):
            continue
        for row in rows[1:]:
            param = _parse_parameter_row(row, extra_force_optional)
            if param is not None:
                out.append(param)
    return out


# ---------------------------------------------------------------------------
# Example-JSON response collapse
# ---------------------------------------------------------------------------


def _extract_example_json(html: str) -> Any | None:
    """Locate the 'Example Response' code block and parse it as JSON.

    Returns None when the section is absent or the body is not valid JSON.
    """
    section = _section(html, _RE_EXAMPLE_HEADING, _RE_ERRORS_HEADING)
    if section is None:
        return None
    sub = HTMLParser(section)
    for code in sub.css("pre, code"):
        raw = (code.text() or "").strip()
        if not raw or raw[0] not in "{[":
            continue
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return None


def _is_plural_of(plural: str | None, singular: str | None) -> bool:
    """English plural-singular pair check.

    Covers the FatSecret docs' standard patterns:
      * foods   -> food
      * recipes -> recipe   (s suffix)
      * food_entries -> food_entry  (ies suffix)
      * food_categories -> food_category
      * food_sub_categories -> food_sub_category
    """
    if not plural or not singular or plural == singular:
        return False
    if plural == singular + "s":
        return True
    if plural == singular + "es":
        return True
    if singular.endswith("y") and plural == singular[:-1] + "ies":
        return True
    # Generic fallback: plural is just singular + 's' (already covered) or
    # has a regular -es / -ies suffix.
    return False


def _singular_of(plural: str) -> str | None:
    """Best-effort inverse of `_is_plural_of`.  Used to repair docs typos
    where the example JSON duplicates the parent key (e.g.
    ``{recipe_types: {recipe_types: [...]}}`` instead of the on-the-wire
    ``{recipe_types: {recipe_type: [...]}}``).
    """
    if plural.endswith("ies") and len(plural) > 3:
        return plural[:-3] + "y"
    # ``-es`` removal only applies when the stem genuinely ends in a sibilant
    # (boxes -> box, dishes -> dish, lurches -> lurch).  Otherwise the plural
    # is just ``stem + s`` and we should drop a single ``s`` (recipe_types ->
    # recipe_type, not recipe_typ).
    if plural.endswith("es") and len(plural) > 2:
        stem = plural[:-2]
        if stem.endswith(("s", "x", "z", "ch", "sh")):
            return stem
    if plural.endswith("s") and len(plural) > 1:
        return plural[:-1]
    return None


def _non_scalar_children(d: dict[str, Any]) -> list[tuple[str, Any]]:
    return [(k, v) for k, v in d.items() if isinstance(v, (dict, list))]


def _walk_response(node: Any, parent_key: str | None) -> Any:
    """Collapse a JSON example into the raw-YAML skeletal response shape.

    See module docstring for the rules.
    """
    if isinstance(node, list):
        return [{}]
    if not isinstance(node, dict):
        return ""

    # FatSecret's ``{ "value": "<scalar>" }`` ID-wrap.  We never preserve the
    # inner ``value`` key — generated code unwraps the outer key directly.
    if (
        len(node) == 1
        and "value" in node
        and not isinstance(node["value"], (dict, list))
    ):
        return ""

    # Repair the docs-typo case: parent key (e.g. ``recipe_types``) has a
    # single child whose key is identical to the parent.  The wire format
    # uses the singular form; substitute it.
    if len(node) == 1 and parent_key is not None:
        only_key = next(iter(node))
        if only_key == parent_key:
            singular = _singular_of(parent_key)
            if singular and singular != parent_key:
                return {singular: [{}]}
        # Singular-of-parent collapse: when this dict has a single child and
        # the parent name is the plural of that child, the wire is "really"
        # a list — the docs JSON example just flattened a one-element array
        # to a singleton object.
        if _is_plural_of(parent_key, only_key):
            return {only_key: [{}]}

    children = _non_scalar_children(node)
    if not children:
        return {}
    if len(children) > 1:
        # Multi-branch dicts can't be expressed as a single unwrap chain.
        return {}

    key, value = children[0]
    if isinstance(value, list):
        return {key: [{}]}
    if isinstance(value, dict) and _is_plural_of(parent_key, key):
        return {key: [{}]}
    return {key: _walk_response(value, key)}


def _collapse_response(j: Any) -> dict[str, Any]:
    """Top-level wrapper that also handles the root mutator pattern."""
    if isinstance(j, dict) and len(j) == 1 and "success" in j:
        inner = j["success"]
        if (
            isinstance(inner, dict)
            and len(inner) == 1
            and "value" in inner
            and not isinstance(inner["value"], (dict, list))
        ):
            return {"success": 1}
    out = _walk_response(j, None)
    if not isinstance(out, dict):
        # Top-level scalar / list — represent as empty dict so callers always
        # get a mapping.  This matches the convention used for ``feedback``.
        return {}
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_page(ref: MethodRef, html: str) -> EndpointSpec:
    tree = HTMLParser(html)
    spec = EndpointSpec(ref=ref)

    spec.deprecated = _detect_deprecated(tree)
    spec.premier = _detect_premier(tree)
    spec.http_verb = _detect_http_verb(html)
    spec.api_method_param = None
    spec.rest_url = _NATIVE_REST_URLS.get((ref.method, ref.version))
    spec.oauth = _detect_oauth(tree)
    spec.scope = _detect_scope(tree)
    extra_force_opt = _FORCE_OPTIONAL_PER_ENDPOINT.get(
        (ref.method, ref.version), frozenset()
    )
    spec.parameters = _parse_parameters(_body_html(tree, html), extra_force_opt)
    spec.notes = _extract_description(tree)

    # Response shape: prefer the XSD (canonical, typed) for endpoints it
    # covers; fall back to walking the HTML "Example Response" JSON block for
    # the v2+ additions and post-v1 endpoints the XSD does not model.
    xsd_shape = _xsd_response_for(ref.method, ref.version)
    example = _extract_example_json(html)
    if xsd_shape is not None:
        spec.response = xsd_shape
    else:
        spec.response = _collapse_response(example) if example is not None else {}

    if not spec.parameters:
        spec.parse_warnings.append("no parameters table found")
    if example is None and xsd_shape is None:
        spec.parse_warnings.append("no example response section found")

    return spec
