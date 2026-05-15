"""Sample tests for representative new _vN methods.

Verifies they invoke _call with the right params (method name, url, json_body)
and that the result is unwrapped correctly. Pattern is consistent across
~80 versioned methods; sampling 8-10 representative ones is sufficient.
"""

from unittest.mock import patch

import pytest

from fatsecret import Fatsecret


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Session"):
        return Fatsecret("ck", "cs")


# ---------------------------------------------------------------------------
# Phase 2 helpers
# ---------------------------------------------------------------------------

def _food(**overrides):
    base = {"food_id": "1", "food_name": "Item", "food_type": "Generic", "food_url": "https://example.com/food"}
    base.update(overrides)
    return base


def _food_entry(**overrides):
    base = {
        "food_entry_id": "1",
        "food_entry_description": "x",
        "date_int": "20250101",
        "meal": "Breakfast",
        "food_id": "1",
        "serving_id": "1",
        "number_of_units": "1",
        "food_entry_name": "x",
        "calories": "100",
        "carbohydrate": "10",
        "protein": "5",
        "fat": "1",
    }
    base.update(overrides)
    return base


# --------------------------- Foods: search ---------------------------


def test_foods_search_v1_call_and_unwrap(fs):
    payload = {"foods": {"food": [_food(food_id="1"), _food(food_id="2")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.search_v1("apple", page_number=0, max_results=10)

    mock_call.assert_called_once()
    params = mock_call.call_args.args[0]
    assert params["method"] == "foods.search"
    assert params["search_expression"] == "apple"
    assert params["page_number"] == 0
    assert params["max_results"] == 10
    assert [r.food_id for r in result] == [1, 2]


def test_foods_search_v1_unwrap_coerces_single_dict(fs):
    payload = {"foods": {"food": _food(food_id="1")}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.foods.search_v1("apple")
    assert [r.food_id for r in result] == [1]


def test_foods_search_v5_call_and_unwrap(fs):
    payload = {
        "foods_search": {
            "results": {"food": [_food(food_id="5")]},
            "max_results": "20",
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.search_v5("banana", food_type="brand")

    params = mock_call.call_args.args[0]
    assert params["method"] == "foods.search.v5"
    assert params["food_type"] == "brand"
    assert [r.food_id for r in result] == [5]


# --------------------------- Foods: get ---------------------------


def test_food_get_v1_call_and_unwrap(fs):
    payload = {"food": _food(food_id="1", food_name="Apple")}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.get_v1("1")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food.get"
    assert params["food_id"] == "1"
    assert result.food_id == 1 and result.food_name == "Apple"


def test_food_get_v5_call_and_unwrap(fs):
    payload = {"food": _food(food_id="5", food_name="Brand Apple")}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.foods.get_v5("5", region="US")

    params = mock_call.call_args.args[0]
    assert params["method"] == "food.get.v5"
    assert params["food_id"] == "5"
    assert params["region"] == "US"
    assert result.food_id == 5 and result.food_name == "Brand Apple"


# --------------------------- food_entries.get ---------------------------


def test_food_entries_get_v2_single_dict_coerced_to_list(fs):
    payload = {"food_entries": {"food_entry": _food_entry(food_entry_id="10")}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_v2(food_entry_id="10")

    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.get.v2"
    assert params["food_entry_id"] == "10"
    assert [r.food_entry_id for r in result] == [10]


def test_food_entries_get_v2_list_passthrough(fs):
    payload = {
        "food_entries": {
            "food_entry": [_food_entry(food_entry_id="10"), _food_entry(food_entry_id="11")]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.diary.entries_get_v2(food_entry_id="10")
    assert [r.food_entry_id for r in result] == [10, 11]


def test_food_entries_get_v2_no_args_returns_empty(fs):
    # Without food_entry_id OR date the method short-circuits with []
    with patch.object(Fatsecret, "_call") as mock_call:
        result = fs.diary.entries_get_v2()
    assert result == []
    mock_call.assert_not_called()


# --------------------------- image_recognition v2 ---------------------------


def test_image_recognition_v2_posts_to_url_with_json_body(fs):
    payload = {"food_response": [_food(food_id="x")]}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.native.image_recognition_v2("BASE64IMG", include_food_data=True)

    # All non-positional kwargs to _call
    kwargs = mock_call.call_args.kwargs
    assert kwargs["url"] == "https://platform.fatsecret.com/rest/image-recognition/v2"
    assert kwargs["method"] == "POST"
    assert kwargs["json_body"]["image_b64"] == "BASE64IMG"
    assert kwargs["json_body"]["include_food_data"] is True
    # `params` is passed by keyword on URL-based endpoints; must NOT carry a
    # `method=` API param (the method arg here means HTTP verb, set above).
    params = kwargs["params"]
    assert "method" not in params
    assert params == {"format": "json"}
    assert result == [_food(food_id="x")]


# --------------------------- profile.get ---------------------------


def test_profile_get_v1_unwraps_profile(fs):
    payload = {"profile": {"nickname": "alice"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile.get_v1()

    params = mock_call.call_args.args[0]
    assert params["method"] == "profile.get"
    _dump = result.model_dump(exclude_unset=True)
    assert _dump.get('nickname') == 'alice'


# --------------------------- recipes ---------------------------


def test_recipe_add_favorite_v1_fixes_singular_bug(fs):
    """The legacy plural typo was `recipes.add_favorites`; v1 uses singular."""
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.add_favorite_v1("rid-1")

    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe.add_favorite"
    assert params["recipe_id"] == "rid-1"
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_recipe_types_get_v1_unwraps_list(fs):
    payload = {"recipe_types": {"recipe_type": ["Breakfast", "Lunch"]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.types_get_v1()

    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe_types.get"
    assert result == ["Breakfast", "Lunch"]
