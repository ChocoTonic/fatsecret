"""Enumerate every (method, version) pair documented on platform.fatsecret.com."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

import httpx
from selectolax.parser import HTMLParser

from .config import GUIDES_HUB, LANDING_MARKER, USER_AGENT, VERSIONS_TO_PROBE
from .http import fetch
from .models import MethodRef

log = logging.getLogger(__name__)

DOC_LINK_RE = re.compile(r"/docs/(v\d+)/([\w.]+)")


def _scrape_sidebar_links(html: str) -> set[tuple[str, str]]:
    """Extract every (version, method) from a docs page's sidebar."""
    tree = HTMLParser(html)
    pairs: set[tuple[str, str]] = set()
    for node in tree.css("a[href]"):
        href = node.attributes.get("href", "")
        m = DOC_LINK_RE.search(href)
        if m:
            pairs.add((m.group(1), m.group(2)))
    return pairs


def _is_real_page(html: str, method: str) -> bool:
    """A real method page has a method-specific heading, not just the landing banner."""
    if LANDING_MARKER in html and method.lower() not in html.lower()[:4000]:
        return False
    tree = HTMLParser(html)
    h1 = tree.css_first("h1")
    if h1 is None:
        return False
    text = (h1.text() or "").strip()
    return bool(text) and LANDING_MARKER not in text


def discover() -> list[MethodRef]:
    """Two-pass discovery:
    1. Seed from the guides hub sidebar.
    2. For every method found, probe every version in VERSIONS_TO_PROBE.
    """
    seed_html = fetch(GUIDES_HUB)
    seeds = _scrape_sidebar_links(seed_html)
    log.info("sidebar seeds: %d", len(seeds))

    methods = sorted({pair[1] for pair in seeds})

    confirmed: set[MethodRef] = set()
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
        for method in methods:
            for version in VERSIONS_TO_PROBE:
                ref = MethodRef(method=method, version=version)
                try:
                    body = fetch(ref.url, client=client)
                except httpx.HTTPStatusError as exc:
                    log.debug("skip %s: %s", ref.url, exc)
                    continue
                if _is_real_page(body, method):
                    confirmed.add(ref)
    log.info("confirmed (method,version) pairs: %d", len(confirmed))
    return sorted(confirmed, key=lambda r: (r.method, r.version))


def group_by_category(refs: Iterable[MethodRef]) -> dict[str, list[MethodRef]]:
    """Heuristic grouping by method-name prefix. Categories match the docs sidebar
    headings so output filenames are stable across runs."""
    buckets: dict[str, list[MethodRef]] = {
        "foods-core": [],
        "foods-aux-and-native": [],
        "recipes": [],
        "profile-foods": [],
        "saved-meals": [],
        "food-diary": [],
        "exercise-weight-profile": [],
    }
    for r in refs:
        m = r.method
        if m in {"foods.search", "food.get"}:
            buckets["foods-core"].append(r)
        elif m in {
            "foods.autocomplete",
            "food.find_id_for_barcode",
            "food_brands.get",
            "food_categories.get",
            "food_sub_categories.get",
            "natural.language.processing",
            "image.recognition",
            "feedback",
        }:
            buckets["foods-aux-and-native"].append(r)
        elif m.startswith("recipe"):
            buckets["recipes"].append(r)
        elif m in {
            "food.create",
            "food.add_favorite",
            "food.delete_favorite",
            "foods.get_favorites",
            "foods.get_most_eaten",
            "foods.get_recently_eaten",
        }:
            buckets["profile-foods"].append(r)
        elif m.startswith("saved_meal"):
            buckets["saved-meals"].append(r)
        elif m.startswith("food_entry") or m.startswith("food_entries"):
            buckets["food-diary"].append(r)
        elif (
            m.startswith("exercise")
            or m.startswith("weight")
            or m.startswith("profile")
        ):
            buckets["exercise-weight-profile"].append(r)
        else:
            buckets.setdefault("uncategorized", []).append(r)
    return {
        k: sorted(v, key=lambda r: (r.method, r.version))
        for k, v in buckets.items()
        if v
    }
