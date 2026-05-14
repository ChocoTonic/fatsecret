"""Parse a single FatSecret method-doc HTML page into an EndpointSpec."""

from __future__ import annotations

import logging
import re

from selectolax.parser import HTMLParser, Node

from .models import EndpointSpec, MethodRef, Parameter

log = logging.getLogger(__name__)


DEPRECATION_PATTERNS = (
    "this is version has been deprecated",
    "this version has been deprecated",
    "deprecated",  # last-resort match; we still gate on banner-style nodes
)


def _text(node: Node | None) -> str:
    return (node.text() if node else "").strip()


def _detect_deprecated(tree: HTMLParser) -> bool:
    """Look for a deprecation banner / callout near the top of the page."""
    for node in tree.css("[class*='deprecat'], [class*='warning'], [class*='banner']"):
        if "deprecat" in (node.text() or "").lower():
            return True
    # Fallback: a leading <p>/<div> with deprecation wording
    for node in tree.css("h1, h2, h3, p"):
        txt = (node.text() or "").lower()
        for pat in DEPRECATION_PATTERNS[:-1]:
            if pat in txt:
                return True
    return False


def _detect_premier(tree: HTMLParser) -> bool:
    body = (tree.body.text() if tree.body else "")
    return "premier" in body.lower() and (
        "premier exclusive" in body.lower() or "* premier" in body.lower()
    )


def _detect_http_verb(tree: HTMLParser) -> str:
    """Look at code samples for the HTTP method. Falls back to GET."""
    for code in tree.css("code, pre"):
        txt = (code.text() or "").strip()
        m = re.search(r"\b(GET|POST|PUT|DELETE|PATCH)\b\s+https?://", txt)
        if m:
            return m.group(1)
    return "GET"


METHOD_PARAM_RE = re.compile(r"method=([\w.]+)")


def _detect_api_method_param(tree: HTMLParser) -> str | None:
    for code in tree.css("code, pre"):
        m = METHOD_PARAM_RE.search(code.text() or "")
        if m:
            return m.group(1)
    return None


REST_URL_RE = re.compile(r"https?://platform\.fatsecret\.com/rest/(?!server\.api)([\w./-]+)")


def _detect_rest_url(tree: HTMLParser) -> str | None:
    for code in tree.css("code, pre"):
        m = REST_URL_RE.search(code.text() or "")
        if m:
            return f"/rest/{m.group(1)}"
    return None


def _parse_parameters_table(tree: HTMLParser) -> list[Parameter]:
    """Find the first table that looks like a 'Parameters' block and extract rows."""
    params: list[Parameter] = []
    target_table = None
    for h in tree.css("h1, h2, h3, h4"):
        if "parameter" in (h.text() or "").lower():
            # the parameters table is usually the next <table> sibling
            sib = h.next
            while sib is not None and sib.tag != "table":
                sib = sib.next
            if sib is not None and sib.tag == "table":
                target_table = sib
                break
    if target_table is None:
        # Fallback: first table on page
        tables = tree.css("table")
        if tables:
            target_table = tables[0]
    if target_table is None:
        return params

    for row in target_table.css("tr"):
        cells = [_text(c) for c in row.css("td")]
        if not cells or len(cells) < 2:
            continue
        name = cells[0]
        # Heuristic: docs often format required-ness as "REQUIRED" / "OPTIONAL" or asterisk
        required = any("required" in c.lower() for c in cells) or name.endswith("*")
        type_ = next((c for c in cells if c.lower() in {"string", "int", "long", "decimal", "boolean", "date"}), None)
        description = cells[-1]
        params.append(
            Parameter(
                name=name.rstrip("*").strip(),
                type=type_,
                required=required,
                description=description,
            )
        )
    return params


def _detect_oauth(tree: HTMLParser) -> list[str]:
    body_text = (tree.body.text() if tree.body else "").lower()
    flows = []
    if "oauth 1" in body_text or "oauth1" in body_text or "hmac-sha1" in body_text:
        flows.append("oauth1")
    if "oauth 2" in body_text or "oauth2" in body_text or "bearer" in body_text:
        flows.append("oauth2")
    return flows or ["oauth1"]


def _detect_scope(tree: HTMLParser) -> str:
    body_text = (tree.body.text() if tree.body else "").lower()
    for candidate in ("premier", "barcode", "nlp", "image-recognition", "feedback", "localization"):
        if f"scope: {candidate}" in body_text or f"\"{candidate}\"" in body_text:
            return candidate
    return "basic"


def parse_page(ref: MethodRef, html: str) -> EndpointSpec:
    tree = HTMLParser(html)
    spec = EndpointSpec(ref=ref)

    spec.deprecated = _detect_deprecated(tree)
    spec.premier = _detect_premier(tree)
    spec.http_verb = _detect_http_verb(tree)
    spec.api_method_param = _detect_api_method_param(tree)
    spec.rest_url = _detect_rest_url(tree) if spec.api_method_param is None else None
    spec.oauth = _detect_oauth(tree)
    spec.scope = _detect_scope(tree)
    spec.parameters = _parse_parameters_table(tree)

    if not spec.parameters:
        spec.parse_warnings.append("no parameters table found")
    if spec.api_method_param is None and spec.rest_url is None:
        spec.parse_warnings.append("could not detect api method= param or REST URL")

    return spec
