"""Exhaustive unit tests for the Food Classification resource.

Covers the six method-version pairs (all Premier-only):
  * food_brands.get          v1, v2
  * food_categories.get      v1, v2
  * food_sub_categories.get  v1, v2

For each method-version we assert:
  1. Happy path: correct `method=` value in params + unwrapped return shape.
  2. Optional params: present when supplied, absent when None.
  3. Single-dict response normalised to a list by `_unwrap`.
  4. Empty / None response coerced to ``[]``.
  5. ``PremierRequiredError`` raised by `_call` propagates to the caller.
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret, PremierRequiredError


def _resolve(obj, dotted_path):
    """Walk a dotted attribute path (e.g. 'foods.search_v5')."""
    for part in dotted_path.split("."):
        obj = getattr(obj, part)
    return obj


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Session"):
        return Fatsecret("ck", "cs")


# ---------------------------------------------------------------------------
# food_brands.get  (v1, v2)
# ---------------------------------------------------------------------------

BRANDS_VERSIONS = [
    ("classification.brands_get_v1", "food_brands.get"),
    ("classification.brands_get_v2", "food_brands.get.v2"),
]


@pytest.mark.parametrize("method_name,api_method", BRANDS_VERSIONS)
def test_food_brands_get_happy_path(fs, method_name, api_method):
    payload = {"food_brands": {"food_brand": ["Brand A", "Brand B"]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)("A")

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["starts_with"] == "A"
    # No optionals supplied → must NOT appear in params.
    assert "brand_type" not in params
    assert "region" not in params
    assert "language" not in params
    assert result == ["Brand A", "Brand B"]


@pytest.mark.parametrize("method_name,api_method", BRANDS_VERSIONS)
def test_food_brands_get_with_all_optionals(fs, method_name, api_method):
    payload = {"food_brands": {"food_brand": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(
            "B",
            brand_type="manufacturer",
            region="US",
            language="en",
        )
    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["starts_with"] == "B"
    assert params["brand_type"] == "manufacturer"
    assert params["region"] == "US"
    assert params["language"] == "en"


@pytest.mark.parametrize("method_name,_api", BRANDS_VERSIONS)
@pytest.mark.parametrize(
    "kwarg,value",
    [("brand_type", "manufacturer"), ("region", "US"), ("language", "en")],
)
def test_food_brands_get_each_optional_param_individually(
    fs, method_name, _api, kwarg, value
):
    payload = {"food_brands": {"food_brand": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)("A", **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value
    # Other optionals stay omitted.
    others = {"brand_type", "region", "language"} - {kwarg}
    for o in others:
        assert o not in params


@pytest.mark.parametrize("method_name,_api", BRANDS_VERSIONS)
def test_food_brands_get_omits_optionals_when_none(fs, method_name, _api):
    payload = {"food_brands": {"food_brand": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)("A", brand_type=None, region=None, language=None)
    params = mock_call.call_args.args[0]
    assert "brand_type" not in params
    assert "region" not in params
    assert "language" not in params


@pytest.mark.parametrize("method_name,_api", BRANDS_VERSIONS)
def test_food_brands_get_single_dict_coerced_to_list(fs, method_name, _api):
    payload = {"food_brands": {"food_brand": "Solo Brand"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)("S")
    assert result == ["Solo Brand"]


@pytest.mark.parametrize("method_name,_api", BRANDS_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"food_brands": None}])
def test_food_brands_get_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)("Z")
    assert result == []


@pytest.mark.parametrize("method_name,_api", BRANDS_VERSIONS)
def test_food_brands_get_propagates_premier_required_error(fs, method_name, _api):
    with patch.object(
        Fatsecret, "_call", side_effect=PremierRequiredError(21, "Premier required")
    ):
        with pytest.raises(PremierRequiredError):
            _resolve(fs, method_name)("A")


# ---------------------------------------------------------------------------
# food_categories.get  (v1, v2)
# ---------------------------------------------------------------------------

CATEGORIES_VERSIONS = [
    ("classification.categories_get_v1", "food_categories.get"),
    ("classification.categories_get_v2", "food_categories.get.v2"),
]


@pytest.mark.parametrize("method_name,api_method", CATEGORIES_VERSIONS)
def test_food_categories_get_happy_path(fs, method_name, api_method):
    payload = {
        "food_categories": {
            "food_category": [
                {"food_category_id": "1", "food_category_name": "Baked Foods"},
                {"food_category_id": "2", "food_category_name": "Beverages"},
            ]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)()

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert "region" not in params
    assert "language" not in params
    assert result == [
        {"food_category_id": "1", "food_category_name": "Baked Foods"},
        {"food_category_id": "2", "food_category_name": "Beverages"},
    ]


@pytest.mark.parametrize("method_name,_api", CATEGORIES_VERSIONS)
@pytest.mark.parametrize(
    "kwarg,value", [("region", "US"), ("language", "en")]
)
def test_food_categories_get_optional_present_when_supplied(
    fs, method_name, _api, kwarg, value
):
    payload = {"food_categories": {"food_category": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(**{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value
    other = "language" if kwarg == "region" else "region"
    assert other not in params


@pytest.mark.parametrize("method_name,_api", CATEGORIES_VERSIONS)
def test_food_categories_get_optionals_absent_when_none(fs, method_name, _api):
    payload = {"food_categories": {"food_category": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(region=None, language=None)
    params = mock_call.call_args.args[0]
    assert "region" not in params
    assert "language" not in params


@pytest.mark.parametrize("method_name,_api", CATEGORIES_VERSIONS)
def test_food_categories_get_single_dict_coerced_to_list(fs, method_name, _api):
    payload = {
        "food_categories": {
            "food_category": {"food_category_id": "1", "food_category_name": "Baked"}
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert result == [{"food_category_id": "1", "food_category_name": "Baked"}]


@pytest.mark.parametrize("method_name,_api", CATEGORIES_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"food_categories": None}])
def test_food_categories_get_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert result == []


@pytest.mark.parametrize("method_name,_api", CATEGORIES_VERSIONS)
def test_food_categories_get_propagates_premier_required_error(fs, method_name, _api):
    with patch.object(
        Fatsecret, "_call", side_effect=PremierRequiredError(21, "Premier required")
    ):
        with pytest.raises(PremierRequiredError):
            _resolve(fs, method_name)()


# ---------------------------------------------------------------------------
# food_sub_categories.get  (v1, v2)
# ---------------------------------------------------------------------------

SUB_CATEGORIES_VERSIONS = [
    ("classification.sub_categories_get_v1", "food_sub_categories.get"),
    ("classification.sub_categories_get_v2", "food_sub_categories.get.v2"),
]


@pytest.mark.parametrize("method_name,api_method", SUB_CATEGORIES_VERSIONS)
def test_food_sub_categories_get_happy_path(fs, method_name, api_method):
    payload = {
        "food_sub_categories": {
            "food_sub_category": ["Breads", "Cakes", "Cookies"]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)("1")

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["food_category_id"] == "1"
    assert "region" not in params
    assert "language" not in params
    assert result == ["Breads", "Cakes", "Cookies"]


@pytest.mark.parametrize("method_name,_api", SUB_CATEGORIES_VERSIONS)
@pytest.mark.parametrize(
    "kwarg,value", [("region", "US"), ("language", "en")]
)
def test_food_sub_categories_get_optional_present_when_supplied(
    fs, method_name, _api, kwarg, value
):
    payload = {"food_sub_categories": {"food_sub_category": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)("7", **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params["food_category_id"] == "7"
    assert params[kwarg] == value
    other = "language" if kwarg == "region" else "region"
    assert other not in params


@pytest.mark.parametrize("method_name,_api", SUB_CATEGORIES_VERSIONS)
def test_food_sub_categories_get_optionals_absent_when_none(fs, method_name, _api):
    payload = {"food_sub_categories": {"food_sub_category": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)("7", region=None, language=None)
    params = mock_call.call_args.args[0]
    assert "region" not in params
    assert "language" not in params


@pytest.mark.parametrize("method_name,_api", SUB_CATEGORIES_VERSIONS)
def test_food_sub_categories_get_single_dict_coerced_to_list(fs, method_name, _api):
    payload = {"food_sub_categories": {"food_sub_category": "Breads"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)("1")
    assert result == ["Breads"]


@pytest.mark.parametrize("method_name,_api", SUB_CATEGORIES_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"food_sub_categories": None}])
def test_food_sub_categories_get_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)("1")
    assert result == []


@pytest.mark.parametrize("method_name,_api", SUB_CATEGORIES_VERSIONS)
def test_food_sub_categories_get_propagates_premier_required_error(
    fs, method_name, _api
):
    with patch.object(
        Fatsecret, "_call", side_effect=PremierRequiredError(21, "Premier required")
    ):
        with pytest.raises(PremierRequiredError):
            _resolve(fs, method_name)("1")
