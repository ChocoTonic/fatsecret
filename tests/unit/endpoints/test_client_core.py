"""Direct unit tests for client core internals not covered by endpoint tests.

Covers:
  * ``_call`` HTTP body (OAuth1 vs OAuth2 paths, defaults, copying, overrides)
  * OAuth1 constructor with ``session_token`` arg
  * ``api_url`` fallback when ``self.oauth`` is None (OAuth2 mode)
  * ``_unwrap`` else branch when ``list_key`` doesn't match
  * ``get_authorize_url`` HMAC-SHA1 signing flow
  * Legacy ``valid_response`` response dispatcher (used only by foods.get_v2)
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret
from fatsecret.errors import (
    ApplicationError,
    AuthenticationError,
    GeneralError,
    ParameterError,
)


# --------------------------- helpers ---------------------------


def _make_oauth1_fs():
    """OAuth1 Fatsecret with mocked OAuth1Service so no network occurs."""
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        mock_oauth1.return_value.base_url = Fatsecret.BASE_URL
        mock_oauth1.return_value.request_token_url = Fatsecret.REQUEST_TOKEN_URL
        mock_oauth1.return_value.authorize_url = Fatsecret.AUTHORIZE_URL
        fs = Fatsecret("ck", "cs")
    return fs


def _make_oauth2_fs():
    return Fatsecret("ck", "cs", auth="oauth2")


def _fake_resp(payload):
    resp = MagicMock()
    resp.json = MagicMock(return_value=payload)
    return resp


# --------------------------- _call ---------------------------


class TestCallHttpBody:
    def test_oauth1_sends_no_authorization_header(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        result = fs._call({"method": "foo.get"})

        assert result == {"ok": True}
        kwargs = fs.session.request.call_args.kwargs
        # OAuth1 path doesn't pass headers
        assert "headers" not in kwargs or kwargs.get("headers") is None

    def test_oauth2_sends_bearer_authorization_header(self):
        fs = _make_oauth2_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        with patch.object(fs, "_get_oauth2_token", return_value="bearer-xyz") as tok:
            fs._call({"method": "foo.get"})

        tok.assert_called_once()
        kwargs = fs.session.request.call_args.kwargs
        assert kwargs["headers"] == {"Authorization": "Bearer bearer-xyz"}

    def test_format_defaults_to_json(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        fs._call({"method": "foo.get"})

        kwargs = fs.session.request.call_args.kwargs
        assert kwargs["params"]["format"] == "json"

    def test_format_not_overridden_when_provided(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        fs._call({"method": "foo.get", "format": "xml"})

        kwargs = fs.session.request.call_args.kwargs
        assert kwargs["params"]["format"] == "xml"

    def test_params_is_copied_not_mutated(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        original = {"method": "foo.get"}
        fs._call(original)

        # caller's dict must not have been mutated with "format"
        assert "format" not in original

    def test_url_arg_overrides_api_url(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        custom_url = "https://platform.fatsecret.com/rest/foods/search/v1"
        fs._call({"method": "ignored"}, url=custom_url)

        args = fs.session.request.call_args.args
        # method, target — target is positional
        assert args[1] == custom_url

    def test_default_target_is_api_url(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        fs._call({"method": "foo.get"})

        args = fs.session.request.call_args.args
        assert args[1] == fs.api_url

    def test_json_body_passed_through(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        body = {"hello": "world"}
        fs._call({"method": "foo.post"}, method="POST", json_body=body)

        call = fs.session.request.call_args
        assert call.kwargs["json"] is body
        assert call.args[0] == "POST"

    def test_method_defaults_to_get(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(return_value=_fake_resp({"ok": True}))

        fs._call({"method": "foo.get"})
        assert fs.session.request.call_args.args[0] == "GET"

    def test_error_envelope_triggers_exception(self):
        fs = _make_oauth1_fs()
        fs.session = MagicMock()
        fs.session.request = MagicMock(
            return_value=_fake_resp({"error": {"code": 2, "message": "auth"}})
        )

        with pytest.raises(AuthenticationError):
            fs._call({"method": "foo.get"})


# --------------------------- OAuth1 session_token ---------------------------


class TestOAuth1SessionToken:
    def test_session_token_sets_access_credentials_and_session(self):
        with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
            session_obj = MagicMock(name="rauth-session")
            mock_oauth1.return_value.get_session.return_value = session_obj

            fs = Fatsecret("ck", "cs", session_token=("tok-A", "sec-B"))

            assert fs.access_token == "tok-A"
            assert fs.access_token_secret == "sec-B"
            # get_session called with the session_token tuple
            mock_oauth1.return_value.get_session.assert_called_once_with(
                token=("tok-A", "sec-B")
            )
            assert fs.session is session_obj


# --------------------------- api_url fallback ---------------------------


class TestApiUrlFallback:
    def test_oauth2_api_url_returns_base_url(self):
        fs = _make_oauth2_fs()
        # fs.oauth is None in OAuth2 mode -> property falls back to BASE_URL
        assert fs.oauth is None
        assert fs.api_url == Fatsecret.BASE_URL


# --------------------------- _unwrap else branch ---------------------------


class TestUnwrapElseBranch:
    def test_list_key_not_in_dict_treats_cur_as_inner(self):
        # _unwrap walks to {"foods": [...]} — cur is now a list (not dict),
        # so list_key="food" doesn't match (the isinstance(cur, dict) check
        # is False) and inner = cur (the list itself).
        payload = {"foods": [{"a": 1}, {"a": 2}]}
        assert Fatsecret._unwrap(payload, "foods", list_key="food") == [
            {"a": 1},
            {"a": 2},
        ]

    def test_list_key_not_in_dict_with_dict_terminal(self):
        # Terminal is a dict, but list_key not in it -> dict is wrapped as
        # a single-element list (since inner is dict not list).
        payload = {"foods": {"other_key": 1}}
        result = Fatsecret._unwrap(payload, "foods", list_key="food")
        assert result == [{"other_key": 1}]


# --------------------------- get_authorize_url ---------------------------


class TestGetAuthorizeUrl:
    def test_signs_request_and_stores_request_token(self):
        fs = _make_oauth1_fs()

        fake_resp = MagicMock()
        fake_resp.text = "oauth_token=req-token-XYZ&oauth_token_secret=req-secret-ABCD"
        fake_resp.raise_for_status = MagicMock()

        with patch(
            "fatsecret.fatsecret.requests.post", return_value=fake_resp
        ) as mock_post:
            url = fs.get_authorize_url(callback_url="oob")

        # POST was made to the request_token endpoint
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == Fatsecret.REQUEST_TOKEN_URL
        # Signed params posted as form data
        data = kwargs["data"]
        assert data["oauth_consumer_key"] == "ck"
        assert data["oauth_signature_method"] == "HMAC-SHA1"
        assert data["oauth_callback"] == "oob"
        assert data["oauth_version"] == "1.0"
        assert "oauth_timestamp" in data
        assert "oauth_nonce" in data
        # HMAC signature is base64-encoded -> non-empty string
        assert isinstance(data["oauth_signature"], str)
        assert len(data["oauth_signature"]) > 0
        # Content-Type form header
        assert kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"

        # Tokens stored
        assert fs.request_token == "req-token-XYZ"
        assert fs.request_token_secret == "req-secret-ABCD"

        # Authorize URL contains the request token
        assert url.startswith(Fatsecret.AUTHORIZE_URL)
        assert "oauth_token=req-token-XYZ" in url

    def test_custom_callback_url_is_signed(self):
        fs = _make_oauth1_fs()
        fake_resp = MagicMock()
        fake_resp.text = "oauth_token=t&oauth_token_secret=s"
        fake_resp.raise_for_status = MagicMock()

        with patch(
            "fatsecret.fatsecret.requests.post", return_value=fake_resp
        ) as mock_post:
            fs.get_authorize_url(callback_url="https://example.com/cb")

        data = mock_post.call_args.kwargs["data"]
        assert data["oauth_callback"] == "https://example.com/cb"


# --------------------------- valid_response legacy ---------------------------


def _resp(payload):
    """Build a fake requests.Response with .json() returning ``payload``."""
    r = MagicMock()
    r.json = MagicMock(return_value=payload)
    return r


class TestValidResponseErrors:
    def test_error_code_2_authentication(self):
        with pytest.raises(AuthenticationError) as ei:
            Fatsecret.valid_response(_resp({"error": {"code": 2, "message": "x"}}))
        assert ei.value.code == 2

    @pytest.mark.parametrize("code", [1, 10, 11, 12, 20, 21])
    def test_error_general_range(self, code):
        with pytest.raises(GeneralError) as ei:
            Fatsecret.valid_response(_resp({"error": {"code": code, "message": "x"}}))
        assert ei.value.code == code

    @pytest.mark.parametrize("code", [3, 4, 5, 6, 7, 8, 9])
    def test_error_auth_range(self, code):
        with pytest.raises(AuthenticationError) as ei:
            Fatsecret.valid_response(_resp({"error": {"code": code, "message": "x"}}))
        assert ei.value.code == code

    @pytest.mark.parametrize("code", [101, 102, 103, 104, 105, 106, 107, 108])
    def test_error_parameter_range(self, code):
        with pytest.raises(ParameterError) as ei:
            Fatsecret.valid_response(_resp({"error": {"code": code, "message": "x"}}))
        assert ei.value.code == code

    @pytest.mark.parametrize("code", [201, 202, 203, 204, 205, 206, 207])
    def test_error_application_range(self, code):
        with pytest.raises(ApplicationError) as ei:
            Fatsecret.valid_response(_resp({"error": {"code": code, "message": "x"}}))
        assert ei.value.code == code


class TestValidResponseBranches:
    def test_success_returns_true(self):
        assert Fatsecret.valid_response(_resp({"success": "1"})) is True

    def test_foods_returns_food_inner(self):
        assert Fatsecret.valid_response(_resp({"foods": {"food": [{"a": 1}]}})) == [
            {"a": 1}
        ]

    def test_suggestions_returns_value(self):
        assert Fatsecret.valid_response(_resp({"suggestions": ["apple", "bread"]})) == [
            "apple",
            "bread",
        ]

    def test_recipes_returns_recipe_inner(self):
        assert Fatsecret.valid_response(
            _resp({"recipes": {"recipe": [{"r": 1}]}})
        ) == [{"r": 1}]

    def test_saved_meals_returns_saved_meal_inner(self):
        assert Fatsecret.valid_response(
            _resp({"saved_meals": {"saved_meal": [{"m": 1}]}})
        ) == [{"m": 1}]

    def test_saved_meal_items_returns_saved_meal_item_inner(self):
        assert Fatsecret.valid_response(
            _resp({"saved_meal_items": {"saved_meal_item": [{"i": 1}]}})
        ) == [{"i": 1}]

    def test_exercise_types_returns_exercise_inner(self):
        assert Fatsecret.valid_response(
            _resp({"exercise_types": {"exercise": [{"e": 1}]}})
        ) == [{"e": 1}]

    def test_food_entries_none_returns_empty_list(self):
        assert Fatsecret.valid_response(_resp({"food_entries": None})) == []

    def test_food_entries_dict_coerced_to_list(self):
        assert Fatsecret.valid_response(
            _resp({"food_entries": {"food_entry": {"id": "1"}}})
        ) == [{"id": "1"}]

    def test_food_entries_list_returned_as_is(self):
        assert Fatsecret.valid_response(
            _resp({"food_entries": {"food_entry": [{"id": "1"}, {"id": "2"}]}})
        ) == [{"id": "1"}, {"id": "2"}]

    def test_month_returns_day_inner(self):
        assert Fatsecret.valid_response(_resp({"month": {"day": [{"d": 1}]}})) == [
            {"d": 1}
        ]

    def test_profile_with_auth_token_returns_tuple(self):
        result = Fatsecret.valid_response(
            _resp({"profile": {"auth_token": "tok", "auth_secret": "sec"}})
        )
        assert result == ("tok", "sec")

    def test_profile_without_auth_token_returns_dict(self):
        result = Fatsecret.valid_response(
            _resp({"profile": {"user_id": "u1"}})
        )
        assert result == {"user_id": "u1"}

    @pytest.mark.parametrize(
        "key,value",
        [
            ("food", {"food_id": "1"}),
            ("recipe", {"recipe_id": "2"}),
            ("recipe_types", {"recipe_type": ["a", "b"]}),
            ("saved_meal_id", "3"),
            ("saved_meal_item_id", "4"),
            ("food_entry_id", "5"),
        ],
    )
    def test_bare_keys_returned_directly(self, key, value):
        assert Fatsecret.valid_response(_resp({key: value})) == value

    def test_empty_response_falls_through(self):
        # Empty dict -> falsy json() -> returns None
        assert Fatsecret.valid_response(_resp({})) is None
