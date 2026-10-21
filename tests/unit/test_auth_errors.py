from unittest.mock import Mock, patch

import pytest
from requests import HTTPError

from fatsecret import Fatsecret


@pytest.mark.parametrize("stage", ["get", "post"])
def test_authenticate_propagates_http_errors(stage):
    session = Mock()
    session.get.return_value.text = (
        '<input name="__VIEWSTATE" value="state">'
        '<input name="__VIEWSTATEGENERATOR" value="generator">'
    )
    error = HTTPError("authentication request failed")
    getattr(session, stage).return_value.raise_for_status.side_effect = error
    with (
        patch("fatsecret.fatsecret.requests.Session", return_value=session),
        patch.object(Fatsecret, "get_authorize_url", return_value="https://example.test/authorize"),
        pytest.raises(HTTPError) as exc,
    ):
        Fatsecret.fatsecret_authenticate("user", "password", "key", "secret")
    assert exc.value is error
    if stage == "get":
        session.post.assert_not_called()


def test_authenticate_propagates_missing_pin():
    session = Mock()
    session.get.return_value.text = (
        '<input name="__VIEWSTATE" value="state">'
        '<input name="__VIEWSTATEGENERATOR" value="generator">'
    )
    session.post.return_value.content = b"<html>Login rejected</html>"
    with (
        patch("fatsecret.fatsecret.requests.Session", return_value=session),
        patch.object(Fatsecret, "get_authorize_url", return_value="https://example.test/authorize"),
        pytest.raises(RuntimeError, match="Failed to find PIN"),
    ):
        Fatsecret.fatsecret_authenticate("user", "password", "key", "secret")
