"""Tests for the transient-failure retry policy.

These exercise the SDK's wiring around `tenacity` (the GET-only gate,
the transient classifier, the `Retry-After` honoring, the opt-out, and
the JSON-error-envelope passthrough). They do not test tenacity itself.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests
import tenacity
from requests.exceptions import ConnectionError, HTTPError, Timeout

from fatsecret import Fatsecret
from fatsecret._retry import _is_transient, default_policy
from fatsecret.errors import AuthenticationError


def _make_response(
    status: int = 200,
    json_body: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.headers = headers or {}
    resp.json.return_value = json_body if json_body is not None else {"foods": {}}
    if 400 <= status < 600:
        err = HTTPError(f"{status} error", response=resp)
        resp.raise_for_status.side_effect = err
    else:
        resp.raise_for_status.return_value = None
    return resp


def _client(retries=True) -> Fatsecret:
    """Build an oauth2 Fatsecret with the request session swapped for a mock."""
    fs = Fatsecret("k", "s", auth="oauth2", retries=retries)
    fs.session = MagicMock()
    fs._oauth2_token = "tok"
    fs._oauth2_token_expires_at = time.time() + 10_000
    return fs


# ---------------------------------------------------------------------------
# classifier
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_is_transient_true_for_transient_http_status(status):
    resp = _make_response(status=status)
    assert _is_transient(HTTPError(response=resp)) is True


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500, 501])
def test_is_transient_false_for_non_transient_http_status(status):
    resp = _make_response(status=status)
    assert _is_transient(HTTPError(response=resp)) is False


def test_is_transient_true_for_connection_and_timeout():
    assert _is_transient(ConnectionError("boom")) is True
    assert _is_transient(Timeout("slow")) is True


def test_is_transient_false_for_unrelated_exception():
    assert _is_transient(ValueError("nope")) is False
    assert _is_transient(AuthenticationError(2, "auth")) is False


def test_is_transient_false_for_httperror_without_response():
    assert _is_transient(HTTPError("no resp")) is False


# ---------------------------------------------------------------------------
# wiring through _call
# ---------------------------------------------------------------------------


def test_get_retries_then_succeeds_on_connection_error():
    fs = _client()
    success = _make_response(json_body={"foods": {"food": []}})
    fs.session.request.side_effect = [
        ConnectionError("net1"),
        ConnectionError("net2"),
        success,
    ]
    with patch("time.sleep"):  # collapse jittered backoff
        result = fs._call({"method": "foods.search"})
    assert fs.session.request.call_count == 3
    assert result == {"foods": {"food": []}}


def test_get_429_honors_numeric_retry_after():
    fs = _client()
    bad = _make_response(status=429, headers={"Retry-After": "0.05"})
    good = _make_response(json_body={"ok": True})
    fs.session.request.side_effect = [bad, good]
    with patch("time.sleep") as sleep_mock:
        fs._call({"method": "foods.search"})
    # The Retry-After header should drive the wait time, not the
    # exponential-jitter base.
    assert sleep_mock.called
    delays = [c.args[0] for c in sleep_mock.call_args_list if c.args]
    assert any(abs(d - 0.05) < 1e-6 for d in delays), delays


def test_post_does_not_retry_on_connection_error():
    fs = _client()
    fs.session.request.side_effect = ConnectionError("net")
    with patch("time.sleep"):
        with pytest.raises(ConnectionError):
            fs._call({"method": "food_entry.edit"}, method="POST")
    assert fs.session.request.call_count == 1


def test_retries_false_disables_retry_loop():
    fs = _client(retries=False)
    fs.session.request.side_effect = ConnectionError("net")
    with pytest.raises(ConnectionError):
        fs._call({"method": "foods.search"})
    assert fs.session.request.call_count == 1
    assert fs._retries is None


def test_custom_retrying_policy_is_used():
    custom = tenacity.Retrying(
        retry=tenacity.retry_if_exception_type(ConnectionError),
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_fixed(0),
        reraise=True,
    )
    fs = _client(retries=custom)
    assert fs._retries is custom
    fs.session.request.side_effect = ConnectionError("net")
    with pytest.raises(ConnectionError):
        fs._call({"method": "foods.search"})
    # 5 attempts vs the default policy's 3.
    assert fs.session.request.call_count == 5


def test_json_error_envelope_with_http_200_raises_typed_not_retried():
    """HTTP 200 with `{"error": {"code": 2}}` body must raise our typed
    exception immediately and NOT be retried."""
    fs = _client()
    envelope = _make_response(
        status=200,
        json_body={"error": {"code": 2, "message": "auth required"}},
    )
    fs.session.request.return_value = envelope
    with pytest.raises(AuthenticationError):
        fs._call({"method": "foods.search"})
    assert fs.session.request.call_count == 1


def test_non_transient_4xx_propagates_immediately():
    fs = _client()
    fs.session.request.return_value = _make_response(status=401)
    with pytest.raises(HTTPError):
        fs._call({"method": "foods.search"})
    assert fs.session.request.call_count == 1


def test_default_policy_caps_at_three_attempts_then_reraises():
    fs = _client()
    fs.session.request.side_effect = ConnectionError("persistent")
    with patch("time.sleep"):
        with pytest.raises(ConnectionError, match="persistent"):
            fs._call({"method": "foods.search"})
    assert fs.session.request.call_count == 3


def test_default_policy_factory_is_a_retrying_instance():
    pol = default_policy()
    assert isinstance(pol, tenacity.Retrying)
