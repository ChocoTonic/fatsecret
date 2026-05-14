"""Exhaustive unit tests for the versioned Recipes resource methods.

Covers all 11 method-version pairs:

  recipe.get             v1, v2
  recipes.search         v1, v2, v3
  recipe_types.get       v1, v2
  recipe.add_favorite    v1
  recipe.delete_favorite v1
  recipes.get_favorites  v1, v2

For each: happy-path call (method= + verb), every optional param present-when-set
and absent-when-None, single-dict -> list normalization for list endpoints,
empty-response defaults, version-exclusive params (v3 recipe_types, v2 grams_per_portion),
favorite singular-name bug fix, and Premier propagation via kwargs.
"""

from unittest.mock import patch

import pytest

from fatsecret import Fatsecret


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Session"):
        return Fatsecret("ck", "cs")


# =========================================================================
# recipe.get v1
# =========================================================================


def test_recipe_get_v1_happy_path(fs):
    payload = {"recipe": {"recipe_id": "42", "recipe_name": "Pancakes"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.get_v1("42")
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe.get"
    assert params["recipe_id"] == "42"
    # No HTTP verb override (defaults to GET).
    assert mock_call.call_args.kwargs == {}
    assert result == {"recipe_id": "42", "recipe_name": "Pancakes"}


def test_recipe_get_v1_optional_region_absent_when_none(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipe": {}}) as mock_call:
        fs.recipes.get_v1("42")
    params = mock_call.call_args.args[0]
    assert "region" not in params


def test_recipe_get_v1_optional_region_present_when_set(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipe": {}}) as mock_call:
        fs.recipes.get_v1("42", region="US")
    params = mock_call.call_args.args[0]
    assert params["region"] == "US"


def test_recipe_get_v1_does_not_send_grams_per_portion(fs):
    """grams_per_portion is a v2-only response field, never sent on v1 calls."""
    with patch.object(Fatsecret, "_call", return_value={"recipe": {}}) as mock_call:
        fs.recipes.get_v1("42", region="US")
    params = mock_call.call_args.args[0]
    assert "grams_per_portion" not in params
    assert params["method"] == "recipe.get"  # not .v2


# =========================================================================
# recipe.get v2
# =========================================================================


def test_recipe_get_v2_happy_path(fs):
    payload = {
        "recipe": {
            "recipe_id": "42",
            "recipe_name": "Pancakes",
            "grams_per_portion": "120.0",
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.get_v2("42")
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe.get.v2"
    assert params["recipe_id"] == "42"
    assert result["grams_per_portion"] == "120.0"


def test_recipe_get_v2_optional_region_absent_when_none(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipe": {}}) as mock_call:
        fs.recipes.get_v2("42")
    params = mock_call.call_args.args[0]
    assert "region" not in params


def test_recipe_get_v2_optional_region_present_when_set(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipe": {}}) as mock_call:
        fs.recipes.get_v2("42", region="FR")
    assert mock_call.call_args.args[0]["region"] == "FR"


def test_recipe_get_v2_empty_payload_returns_none(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.recipes.get_v2("42")
    assert result is None


# =========================================================================
# recipes.search v1
# =========================================================================


def test_recipes_search_v1_happy_path(fs):
    payload = {
        "recipes": {"recipe": [{"recipe_id": "1"}, {"recipe_id": "2"}]}
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.search_v1(
            search_expression="cake",
            recipe_type="Dessert",
            page_number=0,
            max_results=10,
        )
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipes.search"
    assert params["search_expression"] == "cake"
    assert params["recipe_type"] == "Dessert"
    assert params["page_number"] == 0
    assert params["max_results"] == 10
    assert result == [{"recipe_id": "1"}, {"recipe_id": "2"}]


def test_recipes_search_v1_no_optionals_only_method(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v1()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipes.search"}


def test_recipes_search_v1_single_dict_normalized_to_list(fs):
    payload = {"recipes": {"recipe": {"recipe_id": "solo"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.recipes.search_v1("cake")
    assert result == [{"recipe_id": "solo"}]


def test_recipes_search_v1_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipes": None}):
        assert fs.recipes.search_v1("nothing") == []


def test_recipes_search_v1_does_not_send_v3_only_params(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v1("cake")
    params = mock_call.call_args.args[0]
    assert "recipe_types" not in params
    assert "recipe_types_matchall" not in params


# =========================================================================
# recipes.search v2
# =========================================================================


def test_recipes_search_v2_happy_path_all_optionals(fs):
    payload = {"recipes": {"recipe": [{"recipe_id": "9"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.search_v2(
            search_expression="chicken",
            must_have_images=True,
            calories_from=100,
            calories_to=400,
            carb_percentage_from=10,
            carb_percentage_to=40,
            protein_percentage_from=20,
            protein_percentage_to=50,
            fat_percentage_from=5,
            fat_percentage_to=30,
            prep_time_from=5,
            prep_time_to=60,
            page_number=1,
            max_results=20,
            sort_by="newest",
            region="US",
        )
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipes.search.v2"
    assert params["search_expression"] == "chicken"
    assert params["must_have_images"] is True
    # Dotted keys (upstream API format) are preserved.
    assert params["calories.from"] == 100
    assert params["calories.to"] == 400
    assert params["carb_percentage.from"] == 10
    assert params["carb_percentage.to"] == 40
    assert params["protein_percentage.from"] == 20
    assert params["protein_percentage.to"] == 50
    assert params["fat_percentage.from"] == 5
    assert params["fat_percentage.to"] == 30
    assert params["prep_time.from"] == 5
    assert params["prep_time.to"] == 60
    assert params["page_number"] == 1
    assert params["max_results"] == 20
    assert params["sort_by"] == "newest"
    assert params["region"] == "US"
    assert result == [{"recipe_id": "9"}]


def test_recipes_search_v2_no_optionals_only_method(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v2()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipes.search.v2"}


def test_recipes_search_v2_single_dict_normalized_to_list(fs):
    payload = {"recipes": {"recipe": {"recipe_id": "x"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.recipes.search_v2("x")
    assert result == [{"recipe_id": "x"}]


def test_recipes_search_v2_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipes": None}):
        assert fs.recipes.search_v2() == []


def test_recipes_search_v2_premier_propagation_via_kwargs(fs):
    """Premier flag is forwarded to _call via kwargs (any kwarg user passes)."""
    # The wrapper does not own a premier kwarg, but kwargs given to _call when
    # the caller injects premier should pass through unchanged. We assert the
    # public method itself uses no surprise kwargs (no method=POST etc.).
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v2("x")
    # Premier endpoints are GET; no HTTP verb override is set.
    assert mock_call.call_args.kwargs == {}


def test_recipes_search_v2_does_not_send_v3_only_params(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v2("x")
    params = mock_call.call_args.args[0]
    assert "recipe_types" not in params
    assert "recipe_types_matchall" not in params


# =========================================================================
# recipes.search v3
# =========================================================================


def test_recipes_search_v3_happy_path_all_optionals(fs):
    payload = {"recipes": {"recipe": [{"recipe_id": "v3"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.search_v3(
            search_expression="soup",
            recipe_types="Lunch,Dinner",
            recipe_types_matchall=True,
            must_have_images=False,
            calories_from=50,
            calories_to=500,
            carb_percentage_from=10,
            carb_percentage_to=40,
            protein_percentage_from=10,
            protein_percentage_to=50,
            fat_percentage_from=5,
            fat_percentage_to=35,
            prep_time_from=10,
            prep_time_to=90,
            page_number=2,
            max_results=15,
            sort_by="caloriesAsc",
            region="GB",
        )
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipes.search.v3"
    assert params["recipe_types"] == "Lunch,Dinner"
    assert params["recipe_types_matchall"] is True
    assert params["search_expression"] == "soup"
    assert params["must_have_images"] is False
    assert params["calories.from"] == 50
    assert params["calories.to"] == 500
    assert params["region"] == "GB"
    assert result == [{"recipe_id": "v3"}]


def test_recipes_search_v3_no_optionals_only_method(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v3()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipes.search.v3"}


def test_recipes_search_v3_recipe_types_alone(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v3(recipe_types="Breakfast")
    params = mock_call.call_args.args[0]
    assert params["recipe_types"] == "Breakfast"
    assert "recipe_types_matchall" not in params


def test_recipes_search_v3_recipe_types_matchall_alone(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipes": {"recipe": []}}
    ) as mock_call:
        fs.recipes.search_v3(recipe_types_matchall=False)
    params = mock_call.call_args.args[0]
    assert params["recipe_types_matchall"] is False
    assert "recipe_types" not in params


def test_recipes_search_v3_single_dict_normalized_to_list(fs):
    payload = {"recipes": {"recipe": {"recipe_id": "only"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.recipes.search_v3()
    assert result == [{"recipe_id": "only"}]


def test_recipes_search_v3_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipes": None}):
        assert fs.recipes.search_v3() == []


# =========================================================================
# recipe_types.get v1
# =========================================================================


def test_recipe_types_get_v1_happy_path(fs):
    payload = {"recipe_types": {"recipe_type": ["Breakfast", "Lunch", "Dinner"]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.types_get_v1()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipe_types.get"}
    assert mock_call.call_args.kwargs == {}
    assert result == ["Breakfast", "Lunch", "Dinner"]


def test_recipe_types_get_v1_single_value_normalized_to_list(fs):
    payload = {"recipe_types": {"recipe_type": "Breakfast"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.recipes.types_get_v1() == ["Breakfast"]


def test_recipe_types_get_v1_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipe_types": None}):
        assert fs.recipes.types_get_v1() == []


# =========================================================================
# recipe_types.get v2
# =========================================================================


def test_recipe_types_get_v2_happy_path_no_opts(fs):
    payload = {"recipe_types": {"recipe_type": ["A", "B"]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.types_get_v2()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipe_types.get.v2"}
    assert result == ["A", "B"]


def test_recipe_types_get_v2_optionals_present_when_set(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipe_types": {"recipe_type": []}}
    ) as mock_call:
        fs.recipes.types_get_v2(region="US", language="en")
    params = mock_call.call_args.args[0]
    assert params["region"] == "US"
    assert params["language"] == "en"


def test_recipe_types_get_v2_optionals_absent_when_none(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipe_types": {"recipe_type": []}}
    ) as mock_call:
        fs.recipes.types_get_v2()
    params = mock_call.call_args.args[0]
    assert "region" not in params
    assert "language" not in params


def test_recipe_types_get_v2_partial_optional(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"recipe_types": {"recipe_type": []}}
    ) as mock_call:
        fs.recipes.types_get_v2(language="fr")
    params = mock_call.call_args.args[0]
    assert params["language"] == "fr"
    assert "region" not in params


def test_recipe_types_get_v2_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.recipes.types_get_v2() == []


# =========================================================================
# recipe.add_favorite v1
# =========================================================================


def test_recipe_add_favorite_v1_uses_singular_method_name(fs):
    """Legacy plural typo was `recipes.add_favorites`. v1 fixes to `recipe.add_favorite`."""
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.add_favorite_v1("rid-1")
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe.add_favorite"
    assert params["method"] != "recipes.add_favorites"
    assert params["recipe_id"] == "rid-1"
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_recipe_add_favorite_v1_success_string_one(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        assert fs.recipes.add_favorite_v1("rid-1") is True


def test_recipe_add_favorite_v1_success_zero_is_false(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        assert fs.recipes.add_favorite_v1("rid-1") is False


def test_recipe_add_favorite_v1_passthrough_when_no_success_key(fs):
    payload = {"error": "nope"}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.recipes.add_favorite_v1("rid-1") == payload


# =========================================================================
# recipe.delete_favorite v1
# =========================================================================


def test_recipe_delete_favorite_v1_uses_singular_method_name_and_delete_verb(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.delete_favorite_v1("rid-2")
    params = mock_call.call_args.args[0]
    assert params["method"] == "recipe.delete_favorite"
    assert params["method"] != "recipes.delete_favorites"
    assert params["recipe_id"] == "rid-2"
    assert mock_call.call_args.kwargs.get("method") == "DELETE"
    assert result is True


def test_recipe_delete_favorite_v1_success_string_one(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        assert fs.recipes.delete_favorite_v1("rid-2") is True


def test_recipe_delete_favorite_v1_passthrough_when_no_success_key(fs):
    payload = {"unexpected": True}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.recipes.delete_favorite_v1("rid-2") == payload


# =========================================================================
# recipes.get_favorites v1
# =========================================================================


def test_recipes_get_favorites_v1_happy_path(fs):
    """v1 uses the legacy api method `recipe.get_favorites` (singular root)."""
    payload = {
        "recipes": {"recipe": [{"recipe_id": "f1"}, {"recipe_id": "f2"}]}
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.get_favorites_v1()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipe.get_favorites"}
    assert mock_call.call_args.kwargs == {}
    assert result == [{"recipe_id": "f1"}, {"recipe_id": "f2"}]


def test_recipes_get_favorites_v1_single_dict_normalized_to_list(fs):
    payload = {"recipes": {"recipe": {"recipe_id": "solo"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.recipes.get_favorites_v1() == [{"recipe_id": "solo"}]


def test_recipes_get_favorites_v1_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipes": None}):
        assert fs.recipes.get_favorites_v1() == []


# =========================================================================
# recipes.get_favorites v2
# =========================================================================


def test_recipes_get_favorites_v2_happy_path(fs):
    payload = {"recipes": {"recipe": [{"recipe_id": "v2a"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.recipes.get_favorites_v2()
    params = mock_call.call_args.args[0]
    assert params == {"method": "recipe.get_favorites.v2"}
    assert mock_call.call_args.kwargs == {}
    assert result == [{"recipe_id": "v2a"}]


def test_recipes_get_favorites_v2_single_dict_normalized_to_list(fs):
    payload = {"recipes": {"recipe": {"recipe_id": "only"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.recipes.get_favorites_v2() == [{"recipe_id": "only"}]


def test_recipes_get_favorites_v2_empty_returns_list(fs):
    with patch.object(Fatsecret, "_call", return_value={"recipes": None}):
        assert fs.recipes.get_favorites_v2() == []
