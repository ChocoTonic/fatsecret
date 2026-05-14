"""Exhaustive unit tests for the Foods resource.

Covers fourteen method-version pairs:

  * foods.search                v1, v2, v3, v4, v5
  * food.get                    v1, v2, v3, v4, v5
  * foods.autocomplete          v1, v2          (Premier)
  * food.find_id_for_barcode    v1, v2          (Premier "barcode" scope)

For each pair we assert:
  1. Happy path: correct ``method=`` value in the params dict handed to
     ``Fatsecret._call`` (or to ``session.get`` for the legacy ``food.get.v2``).
  2. Required params propagated.
  3. Every optional parameter is forwarded when supplied AND absent when
     ``None`` (parametrized).
  4. ``_unwrap`` list-coercion: a payload whose inner key is a single dict is
     turned into ``[dict]``.
  5. Empty response: list-returning methods return ``[]``, object-returning
     methods return ``None`` or ``{}``.
  6. Premier propagation: ``PremierRequiredError`` raised inside ``_call``
     bubbles up unchanged.
  7. ``foods.search_v5``'s ``food_type`` enum (none|generic|brand) passes
     through as a raw string.

``_call`` and ``_unwrap`` themselves are tested elsewhere; we always mock
``_call`` so no HTTP is exercised.
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret
from fatsecret.errors import PremierRequiredError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        return Fatsecret("ck", "cs")


# ---------------------------------------------------------------------------
# foods.search v1 - v5
# ---------------------------------------------------------------------------


SEARCH_METHOD_NAMES = {
    1: "foods.search",
    2: "foods.search.v2",
    3: "foods.search.v3",
    4: "foods.search.v4",
    5: "foods.search.v5",
}


def _search_payload_v1(items):
    return {"foods": {"food": items}}


def _search_payload_v2plus(items):
    # v2..v5 share the same unwrap path: foods_search -> results -> food
    return {"foods_search": {"results": {"food": items}, "max_results": "10"}}


def _call_search(fs, version, **kwargs):
    return getattr(fs.foods, f"search_v{version}")("apple", **kwargs)


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_foods_search_happy_path(fs, version):
    items = [{"food_id": "1"}, {"food_id": "2"}]
    payload = _search_payload_v1(items) if version == 1 else _search_payload_v2plus(items)
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _call_search(fs, version)

    mock_call.assert_called_once()
    params = mock_call.call_args.args[0]
    assert params["method"] == SEARCH_METHOD_NAMES[version]
    assert params["search_expression"] == "apple"
    # GET methods don't override _call's default `method` kwarg.
    assert mock_call.call_args.kwargs.get("method", "GET") == "GET"
    assert mock_call.call_args.kwargs.get("url") is None
    assert mock_call.call_args.kwargs.get("json_body") is None
    assert result == items


# Optional-parameter forwarding. Each pair = (kwarg_name, sample_value, supported_versions).
_SEARCH_OPTIONALS = [
    ("page_number", 0, {1, 2, 3, 4, 5}),
    ("max_results", 25, {1, 2, 3, 4, 5}),
    ("generic_description", "Apple", {1}),
    ("include_sub_categories", True, {2, 3, 4, 5}),
    ("include_food_images", True, {3, 4, 5}),
    ("include_food_attributes", True, {3, 4, 5}),
    ("flag_default_serving", True, {2, 3, 4, 5}),
    ("food_type", "brand", {5}),
    ("region", "US", {1, 2, 3, 4, 5}),
    ("language", "en", {1, 2, 3, 4, 5}),
]


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("kwarg,value,supported", _SEARCH_OPTIONALS)
def test_foods_search_optional_forwarding(fs, version, kwarg, value, supported):
    if version not in supported:
        pytest.skip(f"{kwarg} not supported on v{version}")
    payload = _search_payload_v1([]) if version == 1 else _search_payload_v2plus([])
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _call_search(fs, version, **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_foods_search_optionals_absent_when_none(fs, version):
    payload = _search_payload_v1([]) if version == 1 else _search_payload_v2plus([])
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _call_search(fs, version)
    params = mock_call.call_args.args[0]
    # None of the optional keys should appear when the caller passed nothing.
    for kwarg, _value, supported in _SEARCH_OPTIONALS:
        if version in supported:
            assert kwarg not in params, f"{kwarg} leaked into params on v{version}"


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_foods_search_single_dict_coerced_to_list(fs, version):
    single = {"food_id": "42"}
    payload = _search_payload_v1(single) if version == 1 else _search_payload_v2plus(single)
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert _call_search(fs, version) == [single]


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_foods_search_empty_response(fs, version):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert _call_search(fs, version) == []


@pytest.mark.parametrize("version", [1, 2, 3, 4, 5])
def test_foods_search_null_inner(fs, version):
    payload = {"foods": None} if version == 1 else {"foods_search": {"results": None}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert _call_search(fs, version) == []


@pytest.mark.parametrize("version", [2, 3, 4, 5])  # v2+ are Premier
def test_foods_search_premier_propagates(fs, version):
    with patch.object(
        Fatsecret,
        "_call",
        side_effect=PremierRequiredError(207, "Premier required"),
    ):
        with pytest.raises(PremierRequiredError):
            _call_search(fs, version)


@pytest.mark.parametrize("food_type", ["none", "generic", "brand"])
def test_foods_search_v5_food_type_enum_passthrough(fs, food_type):
    payload = _search_payload_v2plus([])
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.foods.search_v5("apple", food_type=food_type)
    assert mock_call.call_args.args[0]["food_type"] == food_type


# ---------------------------------------------------------------------------
# food.get v1 - v5
# ---------------------------------------------------------------------------


GET_METHOD_NAMES = {
    1: "food.get",
    2: "food.get.v2",
    3: "food.get.v3",
    4: "food.get.v4",
    5: "food.get.v5",
}


# Optional kwarg, sample value, supported version set.
_GET_OPTIONALS = [
    ("include_sub_categories", True, {1, 3, 4, 5}),
    ("flag_default_serving", True, {1, 3, 4, 5}),
    ("include_food_images", True, {4, 5}),
    ("include_food_attributes", True, {4, 5}),
    ("region", "US", {1, 2, 3, 4, 5}),
    ("language", "en", {1, 2, 3, 4, 5}),
]


# `foods.get_v2` is a legacy method: it uses `session.get` + `valid_response`
# directly, rather than `_call`. We test it with a session-level mock.


def _mock_session_response(json_data):
    resp = MagicMock()
    resp.json.return_value = json_data
    return resp


@pytest.mark.parametrize("version", [1, 3, 4, 5])
def test_food_get_happy_path(fs, version):
    food_obj = {"food_id": str(version), "food_name": f"Food v{version}"}
    payload = {"food": food_obj}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs.foods, f"get_v{version}")("abc")
    params = mock_call.call_args.args[0]
    assert params["method"] == GET_METHOD_NAMES[version]
    assert params["food_id"] == "abc"
    assert mock_call.call_args.kwargs.get("method", "GET") == "GET"
    assert result == food_obj


def test_food_get_v2_happy_path(fs):
    food_obj = {"food_id": "2", "food_name": "Food v2"}
    fs.session.get = MagicMock(return_value=_mock_session_response({"food": food_obj}))
    result = fs.foods.get_v2("abc")

    fs.session.get.assert_called_once()
    params = fs.session.get.call_args.kwargs["params"]
    assert params["method"] == "food.get.v2"
    assert params["food_id"] == "abc"
    assert params["format"] == "json"
    assert "region" not in params
    assert "language" not in params
    assert result == food_obj


def test_food_get_v2_optional_forwarding(fs):
    fs.session.get = MagicMock(return_value=_mock_session_response({"food": {}}))
    fs.foods.get_v2("x", region="US", language="en")
    params = fs.session.get.call_args.kwargs["params"]
    assert params["region"] == "US"
    assert params["language"] == "en"


@pytest.mark.parametrize("version", [1, 3, 4, 5])
@pytest.mark.parametrize("kwarg,value,supported", _GET_OPTIONALS)
def test_food_get_optional_forwarding(fs, version, kwarg, value, supported):
    if version not in supported:
        pytest.skip(f"{kwarg} not supported on v{version}")
    with patch.object(Fatsecret, "_call", return_value={"food": {}}) as mock_call:
        getattr(fs.foods, f"get_v{version}")("abc", **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value


@pytest.mark.parametrize("version", [1, 3, 4, 5])
def test_food_get_optionals_absent_when_none(fs, version):
    with patch.object(Fatsecret, "_call", return_value={"food": {}}) as mock_call:
        getattr(fs.foods, f"get_v{version}")("abc")
    params = mock_call.call_args.args[0]
    for kwarg, _value, supported in _GET_OPTIONALS:
        if version in supported:
            assert kwarg not in params


@pytest.mark.parametrize("version", [1, 3, 4, 5])
def test_food_get_empty_response(fs, version):
    with patch.object(Fatsecret, "_call", return_value={}):
        # `_unwrap(payload, "food")` returns None when key missing.
        assert getattr(fs.foods, f"get_v{version}")("abc") is None


# ---------------------------------------------------------------------------
# foods.autocomplete v1, v2
# ---------------------------------------------------------------------------


AUTOCOMPLETE_METHOD_NAMES = {1: "foods.autocomplete", 2: "foods.autocomplete.v2"}


@pytest.mark.parametrize("version", [1, 2])
def test_foods_autocomplete_happy_path(fs, version):
    payload = {"suggestions": {"suggestion": ["apple", "apricot"]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs.foods, f"autocomplete_v{version}")("ap")

    params = mock_call.call_args.args[0]
    assert params["method"] == AUTOCOMPLETE_METHOD_NAMES[version]
    assert params["expression"] == "ap"
    assert "max_results" not in params
    assert "region" not in params
    assert result == ["apple", "apricot"]


@pytest.mark.parametrize("version", [1, 2])
@pytest.mark.parametrize(
    "kwarg,value",
    [("max_results", 10), ("region", "US")],
)
def test_foods_autocomplete_optional_forwarding(fs, version, kwarg, value):
    payload = {"suggestions": {"suggestion": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        getattr(fs.foods, f"autocomplete_v{version}")("ap", **{kwarg: value})
    assert mock_call.call_args.args[0][kwarg] == value


@pytest.mark.parametrize("version", [1, 2])
def test_foods_autocomplete_single_string_coerced_to_list(fs, version):
    payload = {"suggestions": {"suggestion": "apple"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert getattr(fs.foods, f"autocomplete_v{version}")("ap") == ["apple"]


@pytest.mark.parametrize("version", [1, 2])
def test_foods_autocomplete_empty_response(fs, version):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert getattr(fs.foods, f"autocomplete_v{version}")("ap") == []


@pytest.mark.parametrize("version", [1, 2])
def test_foods_autocomplete_premier_propagates(fs, version):
    with patch.object(
        Fatsecret,
        "_call",
        side_effect=PremierRequiredError(207, "Premier required"),
    ):
        with pytest.raises(PremierRequiredError):
            getattr(fs.foods, f"autocomplete_v{version}")("ap")


# ---------------------------------------------------------------------------
# food.find_id_for_barcode v1, v2
# ---------------------------------------------------------------------------


BARCODE_METHOD_NAMES = {1: "food.find_id_for_barcode", 2: "food.find_id_for_barcode.v2"}


def test_food_find_id_for_barcode_v1_happy_path(fs):
    payload = {"food_id": {"value": "12345"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.find_id_for_barcode_v1("0049000028911")

    params = mock_call.call_args.args[0]
    assert params["method"] == BARCODE_METHOD_NAMES[1]
    assert params["barcode"] == "0049000028911"
    assert "region" not in params
    assert "language" not in params
    assert result == {"value": "12345"}


@pytest.mark.parametrize(
    "kwarg,value",
    [("region", "US"), ("language", "en")],
)
def test_food_find_id_for_barcode_v1_optional_forwarding(fs, kwarg, value):
    payload = {"food_id": {"value": "0"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.foods.find_id_for_barcode_v1("0049000028911", **{kwarg: value})
    assert mock_call.call_args.args[0][kwarg] == value


def test_food_find_id_for_barcode_v1_no_match_returns_zero_envelope(fs):
    payload = {"food_id": {"value": "0"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.foods.find_id_for_barcode_v1("0000000000000") == {"value": "0"}


def test_food_find_id_for_barcode_v1_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.foods.find_id_for_barcode_v1("0000000000000") is None


def test_food_find_id_for_barcode_v2_happy_path(fs):
    food_obj = {"food_id": "12345", "food_name": "Coke 12oz"}
    payload = {"food": food_obj}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.find_id_for_barcode_v2("0049000028911")
    params = mock_call.call_args.args[0]
    assert params["method"] == BARCODE_METHOD_NAMES[2]
    assert params["barcode"] == "0049000028911"
    for opt in (
        "include_sub_categories",
        "include_food_images",
        "include_food_attributes",
        "flag_default_serving",
        "region",
        "language",
    ):
        assert opt not in params
    assert result == food_obj


@pytest.mark.parametrize(
    "kwarg,value",
    [
        ("include_sub_categories", True),
        ("include_food_images", True),
        ("include_food_attributes", True),
        ("flag_default_serving", True),
        ("region", "US"),
        ("language", "en"),
    ],
)
def test_food_find_id_for_barcode_v2_optional_forwarding(fs, kwarg, value):
    payload = {"food": {}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.foods.find_id_for_barcode_v2("0049000028911", **{kwarg: value})
    assert mock_call.call_args.args[0][kwarg] == value


def test_food_find_id_for_barcode_v2_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.foods.find_id_for_barcode_v2("0049000028911") is None


@pytest.mark.parametrize("version", [1, 2])
def test_food_find_id_for_barcode_premier_propagates(fs, version):
    with patch.object(
        Fatsecret,
        "_call",
        side_effect=PremierRequiredError(207, "Premier (barcode) required"),
    ):
        with pytest.raises(PremierRequiredError):
            getattr(fs.foods, f"find_id_for_barcode_v{version}")("0049000028911")
