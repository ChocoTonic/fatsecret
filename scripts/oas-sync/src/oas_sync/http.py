"""HTTP client with on-disk caching keyed by URL."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import CACHE_DIR, REQUEST_TIMEOUT_S, USER_AGENT

log = logging.getLogger(__name__)


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.html"


@retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=10))
def _fetch_remote(url: str, client: httpx.Client) -> str:
    resp = client.get(url, timeout=REQUEST_TIMEOUT_S, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def fetch(url: str, *, force: bool = False, client: httpx.Client | None = None) -> str:
    """Fetch URL with on-disk cache. Same URL → same bytes, forever (until --force)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url)
    if path.exists() and not force:
        log.debug("cache hit: %s", url)
        return path.read_text(encoding="utf-8")

    owns_client = client is None
    if owns_client:
        client = httpx.Client(headers={"User-Agent": USER_AGENT})
    try:
        log.info("fetch: %s", url)
        body = _fetch_remote(url, client)
        path.write_text(body, encoding="utf-8")
        return body
    finally:
        if owns_client:
            client.close()


def cached(url: str) -> str | None:
    path = _cache_path(url)
    return path.read_text(encoding="utf-8") if path.exists() else None
