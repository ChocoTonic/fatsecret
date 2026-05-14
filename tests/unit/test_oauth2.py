"""OAuth2 init and token-flow unit tests. No real HTTP calls."""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret


def _fake_token_response(access_token="tok-abc", expires_in=3600):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
    )
    return resp


class TestOAuth2Init:
    def test_oauth2_constructor_does_not_make_http_calls(self):
        # Patch BOTH requests.post (token fetch) and OAuth1Service so importing/instantiating
        # never touches the network even on accidental fallbacks.
        with patch("fatsecret.fatsecret.requests.post") as mock_post, patch(
            "fatsecret.fatsecret.OAuth1Service"
        ) as mock_oauth1:
            fs = Fatsecret(
                "ck",
                "cs",
                auth="oauth2",
                scopes=["basic", "premier"],
            )
            assert fs.auth_mode == "oauth2"
            assert fs.scopes == ["basic", "premier"]
            # oauth1 service must NOT have been constructed
            mock_oauth1.assert_not_called()
            # No HTTP token call during __init__
            mock_post.assert_not_called()
            # Token cache should be unset
            assert fs._oauth2_token is None
            assert fs._oauth2_token_expires_at == 0.0

    def test_oauth1_default_auth_mode(self):
        with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
            mock_oauth1.return_value.get_session.return_value = MagicMock()
            fs = Fatsecret("ck", "cs")
            assert fs.auth_mode == "oauth1"
            mock_oauth1.assert_called_once()

    def test_invalid_auth_value_raises(self):
        with pytest.raises(ValueError) as exc_info:
            Fatsecret("ck", "cs", auth="invalid")  # type: ignore[arg-type]
        assert "oauth1" in str(exc_info.value) and "oauth2" in str(exc_info.value)


class TestGetOauth2Token:
    def _make_fs(self):
        with patch("fatsecret.fatsecret.OAuth1Service"):
            return Fatsecret("ck", "cs", auth="oauth2", scopes=["basic"])

    def test_fetches_and_returns_access_token(self):
        fs = self._make_fs()
        with patch(
            "fatsecret.fatsecret.requests.post",
            return_value=_fake_token_response(access_token="bearer-1"),
        ) as mock_post:
            token = fs._get_oauth2_token()

        assert token == "bearer-1"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        # URL is positional
        assert args[0] == Fatsecret.OAUTH2_TOKEN_URL
        # Form-encoded grant_type
        assert kwargs["data"]["grant_type"] == "client_credentials"
        assert kwargs["data"]["scope"] == "basic"
        # Basic auth tuple (consumer_key, consumer_secret)
        assert kwargs["auth"] == ("ck", "cs")

    def test_token_is_cached_across_calls(self):
        fs = self._make_fs()
        with patch(
            "fatsecret.fatsecret.requests.post",
            return_value=_fake_token_response(access_token="bearer-cache"),
        ) as mock_post:
            first = fs._get_oauth2_token()
            second = fs._get_oauth2_token()

        assert first == second == "bearer-cache"
        # Cache hit: post was only called the first time
        assert mock_post.call_count == 1

    def test_no_scopes_omits_scope_param(self):
        with patch("fatsecret.fatsecret.OAuth1Service"):
            fs = Fatsecret("ck", "cs", auth="oauth2")  # no scopes
        with patch(
            "fatsecret.fatsecret.requests.post",
            return_value=_fake_token_response(),
        ) as mock_post:
            fs._get_oauth2_token()
        assert "scope" not in mock_post.call_args.kwargs["data"]
