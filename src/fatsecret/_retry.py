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

import tenacity
from requests.exceptions import ConnectionError, HTTPError, Timeout

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


def _wait_with_retry_after(retry_state: tenacity.RetryCallState) -> float:
    """Honor a numeric `Retry-After` header when present, else exponential jitter.

    HTTP-date forms of `Retry-After` are intentionally not parsed here —
    in practice FatSecret's gateways send numeric seconds, and date
    parsing introduces timezone edge cases that aren't worth the surface
    area for a retry path.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, HTTPError) and getattr(exc, "response", None) is not None:
        ra = exc.response.headers.get("Retry-After")
        if ra:
            try:
                return float(ra)
            except ValueError:
                pass
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
    """Build the default retry policy: 3 attempts, 30s total cap, full jitter."""
    return tenacity.Retrying(
        retry=tenacity.retry_if_exception(_is_transient),
        wait=_wait_with_retry_after,
        stop=tenacity.stop_after_attempt(3) | tenacity.stop_after_delay(30),
        before_sleep=_log_retry,
        reraise=True,
    )
