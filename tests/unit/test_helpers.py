"""Unit tests for the static/instance helpers introduced in v1.0:
_check_errors and _unwrap."""

import pytest

from fatsecret import Fatsecret
from fatsecret.errors import (
    ApplicationError,
    AuthenticationError,
    GeneralError,
    ParameterError,
    PremierRequiredError,
    ScopeRequiredError,
)


# --------------------------- _check_errors ---------------------------


class TestCheckErrors:
    """Error code -> exception class mapping (no return value, raises only)."""

    def test_no_error_key_is_noop(self):
        # Should not raise
        Fatsecret._check_errors({"food": {"food_id": "1"}})

    def test_empty_error_value_is_noop(self):
        Fatsecret._check_errors({"error": None})
        Fatsecret._check_errors({"error": {}})

    def test_non_dict_payload_is_noop(self):
        # Lists and scalars are not error envelopes
        Fatsecret._check_errors([{"foo": 1}])
        Fatsecret._check_errors("string-payload")
        Fatsecret._check_errors(None)
        Fatsecret._check_errors(42)

    def test_authentication_error_code_2(self):
        with pytest.raises(AuthenticationError) as exc_info:
            Fatsecret._check_errors({"error": {"code": 2, "message": "auth"}})
        assert exc_info.value.code == 2

    @pytest.mark.parametrize("code", [3, 4, 5, 6, 7, 8, 9])
    def test_authentication_error_range(self, code):
        with pytest.raises(AuthenticationError) as exc_info:
            Fatsecret._check_errors({"error": {"code": code, "message": "auth"}})
        assert exc_info.value.code == code

    @pytest.mark.parametrize("code", [1, 10, 11, 12, 13, 14, 20, 21, 22, 23, 24])
    def test_general_error_range(self, code):
        with pytest.raises(GeneralError) as exc_info:
            Fatsecret._check_errors({"error": {"code": code, "message": "general"}})
        assert exc_info.value.code == code

    @pytest.mark.parametrize("code", [101, 102, 103, 104, 105, 106, 107, 108, 109])
    def test_parameter_error_range(self, code):
        with pytest.raises(ParameterError) as exc_info:
            Fatsecret._check_errors({"error": {"code": code, "message": "param"}})
        assert exc_info.value.code == code

    def test_premier_required_error_code_207(self):
        with pytest.raises(PremierRequiredError) as exc_info:
            Fatsecret._check_errors(
                {"error": {"code": 207, "message": "premier required"}}
            )
        assert exc_info.value.code == 207
        # PremierRequiredError is a ScopeRequiredError and ApplicationError
        assert isinstance(exc_info.value, ScopeRequiredError)
        assert isinstance(exc_info.value, ApplicationError)

    @pytest.mark.parametrize("code", [208, 211])
    def test_scope_required_error_codes(self, code):
        with pytest.raises(ScopeRequiredError) as exc_info:
            Fatsecret._check_errors({"error": {"code": code, "message": "scope"}})
        # 208/211 should be ScopeRequiredError but NOT PremierRequiredError
        assert exc_info.value.code == code
        assert not isinstance(exc_info.value, PremierRequiredError)

    @pytest.mark.parametrize("code", [201, 202, 203, 204, 205, 206, 209, 210])
    def test_application_error_range(self, code):
        with pytest.raises(ApplicationError) as exc_info:
            Fatsecret._check_errors({"error": {"code": code, "message": "app"}})
        assert exc_info.value.code == code

    def test_unknown_code_falls_back_to_application_error(self):
        with pytest.raises(ApplicationError) as exc_info:
            Fatsecret._check_errors({"error": {"code": 999, "message": "weird"}})
        assert exc_info.value.code == 999


# --------------------------- _unwrap ---------------------------


class TestUnwrap:
    """Walks the envelope; list_key coerces single-dict -> list."""

    def test_single_level_path(self):
        payload = {"food": {"food_id": "1", "name": "apple"}}
        assert Fatsecret._unwrap(payload, "food") == {
            "food_id": "1",
            "name": "apple",
        }

    def test_nested_path(self):
        payload = {"foods_search": {"results": {"food": [{"a": 1}, {"a": 2}]}}}
        assert Fatsecret._unwrap(
            payload, "foods_search", "results", list_key="food"
        ) == [{"a": 1}, {"a": 2}]

    def test_list_key_coerces_single_dict_to_list(self):
        payload = {"foods": {"food": {"food_id": "1"}}}
        assert Fatsecret._unwrap(payload, "foods", list_key="food") == [
            {"food_id": "1"}
        ]

    def test_list_key_returns_empty_list_when_value_is_none(self):
        payload = {"foods": None}
        assert Fatsecret._unwrap(payload, "foods", list_key="food") == []

    def test_list_key_returns_empty_list_when_terminal_is_none(self):
        # Container exists but the terminal value is explicitly None.
        payload = {"foods": {"food": None}}
        assert Fatsecret._unwrap(payload, "foods", list_key="food") == []

    def test_list_key_passes_through_existing_list(self):
        payload = {"foods": {"food": [{"a": 1}]}}
        assert Fatsecret._unwrap(payload, "foods", list_key="food") == [{"a": 1}]

    def test_returns_none_when_path_missing_without_list_key(self):
        payload = {"foo": {"bar": 1}}
        assert Fatsecret._unwrap(payload, "missing") is None

    def test_returns_empty_when_path_missing_with_list_key(self):
        payload = {"foo": {"bar": 1}}
        assert Fatsecret._unwrap(payload, "missing", list_key="x") == []

    def test_non_dict_intermediate_with_list_key(self):
        payload = {"foo": "not-a-dict"}
        assert Fatsecret._unwrap(payload, "foo", "deeper", list_key="x") == []

    def test_non_dict_intermediate_without_list_key(self):
        payload = {"foo": "not-a-dict"}
        assert Fatsecret._unwrap(payload, "foo", "deeper") is None

    def test_empty_path_returns_payload(self):
        payload = {"food_response": [{"a": 1}]}
        assert Fatsecret._unwrap(payload) is payload
