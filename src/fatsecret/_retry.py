"""Transient-failure retry policy for the FatSecret client.

Wraps GET requests in `Fatsecret._call` with an exponential-backoff +
full-jitter retry loop. Retries are limited to genuine transport-level
failures (connection errors, timeouts) and a small set of HTTP status
codes (`429`, `502`, `503`, `504`). Everything else — including 4xx
auth/validation errors and the SDK's own typed exceptions raised from
FatSecret JSON error envelopes — propagates immediately.

This module is intentionally self-contained: it does not import from
`fatsecret.fatsecret` to avoid a circular dependency.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import tenacity
from requests.exceptions import ConnectionError, HTTPError, Timeout

RetryPolicy = bool | tenacity.Retrying

# HTTP status codes treated as transient. Other 5xx (notably 500/501)
# are NOT retried because they often reflect a server-side bug or
# corrupted state where a silent retry would mask the real problem.
_TRANSIENT_STATUS = frozenset({429, 502, 503, 504})


def _is_transient(exc: BaseException) -> bool:
    """Return True if `exc` represents a transient transport failure."""
    if isinstance(exc, (ConnectionError, Timeout)):
        return True
    if isinstance(exc, HTTPError):
        resp = getattr(exc, "response", None)
        return resp is not None and resp.status_code in _TRANSIENT_STATUS
    return False


def parse_retry_after(
    value: str | None, *, now: datetime | None = None
) -> float | None:
    """Parse delta-seconds or an HTTP-date without capping the server delay."""

    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        deadline = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=UTC)
    current = now or datetime.now(UTC)
    return max(0.0, (deadline - current).total_seconds())


def _wait_with_retry_after(retry_state: tenacity.RetryCallState) -> float:
    """Honor `Retry-After` when present, else use exponential jitter."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, HTTPError) and getattr(exc, "response", None) is not None:
        delay = parse_retry_after(exc.response.headers.get("Retry-After"))
        if delay is not None:
            return delay
    return tenacity.wait_exponential_jitter(initial=1, max=10, jitter=2)(retry_state)


def _log_retry(retry_state: tenacity.RetryCallState) -> None:
    """Emit a single stderr WARNING line whenever a retry actually fires."""
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    reason: str
    if isinstance(exc, HTTPError) and getattr(exc, "response", None) is not None:
        reason = f"HTTP {exc.response.status_code}"
    elif exc is not None:
        reason = type(exc).__name__
    else:
        reason = "unknown"
    print(
        f"WARNING fatsecret: retrying after {reason} "
        f"(attempt {retry_state.attempt_number})",
        file=sys.stderr,
    )


def default_policy() -> tenacity.Retrying:
    """Build the default policy: 3 attempts and authoritative Retry-After."""
    return tenacity.Retrying(
        retry=tenacity.retry_if_exception(_is_transient),
        wait=_wait_with_retry_after,
        stop=tenacity.stop_after_attempt(3),
        before_sleep=_log_retry,
        reraise=True,
    )


def resolve_retry_policy(retries: RetryPolicy) -> tenacity.Retrying | None:
    """Normalize the public retry setting used by both HTTP clients."""

    if retries is False:
        return None
    if isinstance(retries, tenacity.Retrying):
        return retries
    return default_policy()


__all__ = ["RetryPolicy", "default_policy", "parse_retry_after", "resolve_retry_policy"]
