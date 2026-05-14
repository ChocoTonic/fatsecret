"""Mocked unit tests for the OAuth1 flow (post requests-oauthlib swap).

These cover the request-token / access-token dance and the
auto-signed outbound API call without touching the network or
needing live FatSecret credentials.
"""

from unittest.mock import MagicMock, patch

from requests_oauthlib import OAuth1Session

from fatsecret import Fatsecret


def _fake_resp(payload):
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    resp.status_code = 200
    return resp


# --------------------------- request-token leg ---------------------------


class TestGetAuthorizeUrlMocked:
    def test_oob_callback_uses_initial_session_and_stores_request_token(self):
        """Default callback_url='oob' uses the session built in __init__."""
        fs = Fatsecret("ck", "cs")

        def fake_fetch(self, url, **kwargs):  # noqa: ANN001
            self._client.client.resource_owner_key = "rtok-1"
            self._client.client.resource_owner_secret = "rsec-1"
            return {"oauth_token": "rtok-1", "oauth_token_secret": "rsec-1"}

        with patch.object(OAuth1Session, "fetch_request_token", new=fake_fetch):
            url = fs.get_authorize_url()  # default oob

        assert fs.request_token == "rtok-1"
        assert fs.request_token_secret == "rsec-1"
        assert url.startswith(Fatsecret.AUTHORIZE_URL)
        assert "oauth_token=rtok-1" in url

    def test_custom_callback_rebuilds_session_with_callback_uri(self):
        def fake_fetch(self, url, **kwargs):  # noqa: ANN001
            self._client.client.resource_owner_key = "rtok-2"
            self._client.client.resource_owner_secret = "rsec-2"
            return {"oauth_token": "rtok-2", "oauth_token_secret": "rsec-2"}

        with patch.object(OAuth1Session, "fetch_request_token", new=fake_fetch):
            fs = Fatsecret("ck", "cs")
            initial_session = fs.session
            url = fs.get_authorize_url(callback_url="https://example.com/cb")

        # Session was swapped for one with the new callback_uri.
        assert fs.session is not initial_session
        assert fs.session._client.client.callback_uri == "https://example.com/cb"
        assert "oauth_token=rtok-2" in url


# --------------------------- access-token leg ---------------------------


class TestAuthenticateMocked:
    def test_authenticate_calls_fetch_access_token_and_stores_tokens(self):
        with patch.object(
            OAuth1Session,
            "fetch_access_token",
            return_value={
                "oauth_token": "atok-1",
                "oauth_token_secret": "asec-1",
            },
        ) as mock_fetch:
            fs = Fatsecret("ck", "cs")
            fs.request_token = "rtok"
            fs.request_token_secret = "rsec"

            result = fs.authenticate("verifier-pin-9999")

        mock_fetch.assert_called_once_with(Fatsecret.ACCESS_TOKEN_URL)
        assert result == ("atok-1", "asec-1")
        assert fs.access_token == "atok-1"
        assert fs.access_token_secret == "asec-1"
        # Session is now a long-lived authed session keyed on the access token.
        assert fs.session._client.client.resource_owner_key == "atok-1"
        assert fs.session._client.client.resource_owner_secret == "asec-1"


# --------------------------- session_token shortcut ---------------------------


class TestSessionTokenShortcut:
    def test_constructor_with_session_token_skips_request_token_flow(self):
        with patch.object(
            OAuth1Session, "fetch_request_token"
        ) as mock_fetch_req, patch.object(
            OAuth1Session, "fetch_access_token"
        ) as mock_fetch_acc:
            fs = Fatsecret("ck", "cs", session_token=("cached-tok", "cached-sec"))

        mock_fetch_req.assert_not_called()
        mock_fetch_acc.assert_not_called()
        assert fs.access_token == "cached-tok"
        assert fs.access_token_secret == "cached-sec"
        assert fs.session._client.client.resource_owner_key == "cached-tok"
        assert fs.session._client.client.resource_owner_secret == "cached-sec"


# --------------------------- signed outbound call ---------------------------


class TestOutboundSigning:
    def test_call_uses_oauth1session_for_signing(self):
        """OAuth1Session is a requests.Session subclass and auto-signs every
        request with an Authorization: OAuth header at the adapter level."""
        fs = Fatsecret("ck", "cs", session_token=("tok", "sec"))

        captured = {}

        def fake_send(self, request, **kwargs):  # noqa: ANN001
            captured["headers"] = dict(request.headers)
            resp = MagicMock()
            resp.status_code = 200
            resp.json = MagicMock(return_value={"ok": True})
            resp.headers = {}
            resp.cookies = MagicMock()
            resp.cookies.__iter__ = MagicMock(return_value=iter([]))
            return resp

        from requests.sessions import Session

        with patch.object(Session, "send", new=fake_send):
            fs._call({"method": "foods.search"})

        auth_header = captured["headers"].get("Authorization", "")
        if isinstance(auth_header, bytes):
            auth_header = auth_header.decode("utf-8")
        assert auth_header.startswith("OAuth "), (
            f"expected OAuth1-signed Authorization header, got: {auth_header!r}"
        )
        # Standard OAuth1 parameter names should appear in the header.
        for piece in (
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
        ):
            assert piece in auth_header


# --------------------------- OAuth2 path untouched ---------------------------


class TestOAuth2PathUntouched:
    def test_oauth2_call_still_injects_bearer_header(self):
        fs = Fatsecret("ck", "cs", auth="oauth2")
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        with patch.object(fs, "_get_oauth2_token", return_value="bearer-XYZ"):
            fs._call({"method": "foods.search"})

        kwargs = fs.session.request.call_args.kwargs
        assert kwargs["headers"] == {"Authorization": "Bearer bearer-XYZ"}
