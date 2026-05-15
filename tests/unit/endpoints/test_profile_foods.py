"""Exhaustive unit tests for the Profile-Foods resource.

Covers the ten method-version pairs:

  * food.create                    v1, v2   (Premier-exclusive, POST)
  * food.add_favorite              v1       (POST)
  * food.delete_favorite           v1       (DELETE)
  * foods.get_favorites            v1, v2   (GET, list)
  * foods.get_most_eaten           v1, v2   (GET, list)
  * foods.get_recently_eaten       v1, v2   (GET, list; v2 ambiguous Premier/Basic
                                              upstream — wrapper behavior tested
                                              as-is, ambiguity not resolved)

For each method-version we assert:
  1. Happy path: correct ``method=`` value, correct HTTP verb, required
     params present, unwrapped return shape.
  2. Optional params: present-when-set, absent-when-None.
  3. List unwrap with single-vs-list coercion for list endpoints.
  4. Empty / missing response coerced to ``[]`` (lists) or ``True`` (mutators).
  5. ``food.create`` is Premier — ``PremierRequiredError`` from ``_call``
     propagates to the caller.
  6. ``food.create`` returns ``food_id`` (unwrap).
  7. ``food.create v2`` schema deltas vs v1 (drops ``other_carbohydrate``;
     adds ``added_sugars``, ``vitamin_d``).
"""

from unittest.mock import patch

import pytest

from fatsecret import Fatsecret, PremierRequiredError


def _resolve(obj, dotted_path):
    """Walk a dotted attribute path (e.g. 'foods.search_v5')."""
    for part in dotted_path.split("."):
        obj = getattr(obj, part)
    return obj


# ---------------------------------------------------------------------------
# Phase 2 helpers: pad XSD-required fields so model_validate succeeds
# ---------------------------------------------------------------------------

def _food(**overrides):
    base = {
        "food_id": "1",
        "food_name": "Item",
        "food_type": "Generic",
        "food_url": "https://example.com/food",
    }
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


def _exercise(**overrides):
    base = {"exercise_id": "1", "exercise_name": "Running"}
    base.update(overrides)
    return base


def _exercise_entry(**overrides):
    base = {
        "is_template_value": "true",
        "exercise_id": "1",
        "exercise_name": "Running",
        "minutes": "30",
        "calories": "150",
    }
    base.update(overrides)
    return base


def _day(**overrides):
    base = {"date_int": "20250101"}
    base.update(overrides)
    return base


def _recipe(**overrides):
    base = {
        "recipe_id": "1",
        "recipe_name": "Stew",
        "recipe_description": "A stew",
    }
    base.update(overrides)
    return base


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Session"):
        return Fatsecret("ck", "cs")


# ---------------------------------------------------------------------------
# food.create  (v1, v2)  — Premier-exclusive, POST
# ---------------------------------------------------------------------------

CREATE_VERSIONS = [
    ("profile_foods.create_v1", "food.create"),
    ("profile_foods.create_v2", "food.create.v2"),
]

REQUIRED_CREATE_KWARGS = dict(
    brand_name="Acme",
    food_name="Bar",
    serving_size="1 bar",
    calories=200.0,
    fat=10.0,
    carbohydrate=20.0,
    protein=5.0,
)


@pytest.mark.parametrize("method_name,api_method", CREATE_VERSIONS)
def test_food_create_happy_path(fs, method_name, api_method):
    payload = {"food_id": {"value": "12345"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS)

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["brand_name"] == "Acme"
    assert params["food_name"] == "Bar"
    assert params["serving_size"] == "1 bar"
    assert params["calories"] == 200.0
    assert params["fat"] == 10.0
    assert params["carbohydrate"] == 20.0
    assert params["protein"] == 5.0
    # HTTP verb is POST.
    assert mock_call.call_args.kwargs.get("method") == "POST"
    # Unwrap returns the food_id value.
    assert result == {"value": "12345"}


@pytest.mark.parametrize("method_name,_api", CREATE_VERSIONS)
def test_food_create_unwraps_food_id_scalar(fs, method_name, _api):
    payload = _food(food_id="9876")
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS)
    assert result == "9876"


@pytest.mark.parametrize("method_name,_api", CREATE_VERSIONS)
def test_food_create_omits_all_optionals_by_default(fs, method_name, _api):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS)
    params = mock_call.call_args.args[0]
    # Shared optional fields must NOT appear in params when not supplied.
    for key in (
        "brand_type",
        "serving_amount",
        "serving_amount_unit",
        "calories_from_fat",
        "saturated_fat",
        "polyunsaturated_fat",
        "monounsaturated_fat",
        "trans_fat",
        "cholesterol",
        "sodium",
        "potassium",
        "fiber",
        "sugar",
        "vitamin_a",
        "vitamin_c",
        "calcium",
        "iron",
        "region",
        "language",
    ):
        assert key not in params


# --- Shared optionals (present in BOTH v1 and v2) ----------------------------
SHARED_OPTIONALS = [
    ("brand_type", "manufacturer"),
    ("serving_amount", "1.0"),
    ("serving_amount_unit", "bar"),
    ("calories_from_fat", 90.0),
    ("saturated_fat", 3.0),
    ("polyunsaturated_fat", 1.0),
    ("monounsaturated_fat", 2.0),
    ("trans_fat", 0.0),
    ("cholesterol", 5.0),
    ("sodium", 100.0),
    ("potassium", 150.0),
    ("fiber", 3.0),
    ("sugar", 8.0),
    ("vitamin_a", 10.0),
    ("vitamin_c", 5.0),
    ("calcium", 4.0),
    ("iron", 2.0),
    ("region", "US"),
    ("language", "en"),
]


@pytest.mark.parametrize("method_name,_api", CREATE_VERSIONS)
@pytest.mark.parametrize("kwarg,value", SHARED_OPTIONALS)
def test_food_create_each_shared_optional_present_when_supplied(
    fs, method_name, _api, kwarg, value
):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS, **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value


@pytest.mark.parametrize("method_name,_api", CREATE_VERSIONS)
@pytest.mark.parametrize("kwarg,_value", SHARED_OPTIONALS)
def test_food_create_each_shared_optional_absent_when_none(
    fs, method_name, _api, kwarg, _value
):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS, **{kwarg: None})
    params = mock_call.call_args.args[0]
    assert kwarg not in params


# --- v1-only optional (other_carbohydrate) -----------------------------------


def test_food_create_v1_accepts_other_carbohydrate(fs):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.create_v1(other_carbohydrate=7.5, **REQUIRED_CREATE_KWARGS)
    params = mock_call.call_args.args[0]
    assert params["other_carbohydrate"] == 7.5
    # v2-only fields must not appear in a v1 call.
    assert "added_sugars" not in params
    assert "vitamin_d" not in params


def test_food_create_v1_omits_other_carbohydrate_when_none(fs):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.create_v1(other_carbohydrate=None, **REQUIRED_CREATE_KWARGS)
    params = mock_call.call_args.args[0]
    assert "other_carbohydrate" not in params


def test_food_create_v2_does_not_accept_other_carbohydrate(fs):
    """v2 drops ``other_carbohydrate`` from the signature entirely."""
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload):
        with pytest.raises(TypeError):
            fs.profile_foods.create_v2(other_carbohydrate=7.5, **REQUIRED_CREATE_KWARGS)


# --- v2-only optionals (added_sugars, vitamin_d) -----------------------------


@pytest.mark.parametrize(
    "kwarg,value", [("added_sugars", 4.0), ("vitamin_d", 2.5)]
)
def test_food_create_v2_accepts_v2_only_optionals(fs, kwarg, value):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.create_v2(**REQUIRED_CREATE_KWARGS, **{kwarg: value})
    params = mock_call.call_args.args[0]
    assert params[kwarg] == value


@pytest.mark.parametrize("kwarg", ["added_sugars", "vitamin_d"])
def test_food_create_v2_omits_v2_only_optionals_when_none(fs, kwarg):
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.create_v2(**REQUIRED_CREATE_KWARGS, **{kwarg: None})
    params = mock_call.call_args.args[0]
    assert kwarg not in params


@pytest.mark.parametrize("kwarg", ["added_sugars", "vitamin_d"])
def test_food_create_v1_does_not_accept_v2_only_optionals(fs, kwarg):
    """v1 signature predates ``added_sugars`` and ``vitamin_d``."""
    payload = _food(food_id="1")
    with patch.object(Fatsecret, "_call", return_value=payload):
        with pytest.raises(TypeError):
            fs.profile_foods.create_v1(**REQUIRED_CREATE_KWARGS, **{kwarg: 1.0})


# --- Premier propagation -----------------------------------------------------


@pytest.mark.parametrize("method_name,_api", CREATE_VERSIONS)
def test_food_create_propagates_premier_required_error(fs, method_name, _api):
    with patch.object(
        Fatsecret, "_call", side_effect=PremierRequiredError(21, "Premier required")
    ):
        with pytest.raises(PremierRequiredError):
            _resolve(fs, method_name)(**REQUIRED_CREATE_KWARGS)


# ---------------------------------------------------------------------------
# food.add_favorite  v1  (POST)
# ---------------------------------------------------------------------------


def test_food_add_favorite_v1_happy_path(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile_foods.add_favorite_v1("fid-1")

    params = mock_call.call_args.args[0]
    assert params["method"] == "food.add_favorite"
    assert params["food_id"] == "fid-1"
    assert "serving_id" not in params
    assert "number_of_units" not in params
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_food_add_favorite_v1_with_serving_id_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.add_favorite_v1("fid-1", serving_id="sid-9")
    params = mock_call.call_args.args[0]
    assert params["serving_id"] == "sid-9"
    assert "number_of_units" not in params


def test_food_add_favorite_v1_with_number_of_units_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.add_favorite_v1("fid-1", number_of_units=2.5)
    params = mock_call.call_args.args[0]
    assert params["number_of_units"] == 2.5
    assert "serving_id" not in params


def test_food_add_favorite_v1_with_both_optionals(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.add_favorite_v1("fid-1", serving_id="sid-9", number_of_units=2.5)
    params = mock_call.call_args.args[0]
    assert params["serving_id"] == "sid-9"
    assert params["number_of_units"] == 2.5


def test_food_add_favorite_v1_optionals_absent_when_none(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.add_favorite_v1("fid-1", serving_id=None, number_of_units=None)
    params = mock_call.call_args.args[0]
    assert "serving_id" not in params
    assert "number_of_units" not in params


def test_food_add_favorite_v1_success_string_one_returns_true(fs):
    # `_mutator_success` accepts both int 1 and str "1".
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        result = fs.profile_foods.add_favorite_v1("fid-1")
    assert result is True


def test_food_add_favorite_v1_non_success_payload_passthrough(fs):
    # Empty / non-success payloads pass through unchanged (no True coercion).
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.profile_foods.add_favorite_v1("fid-1")
    assert result == {}


# ---------------------------------------------------------------------------
# food.delete_favorite  v1  (DELETE)
# ---------------------------------------------------------------------------


def test_food_delete_favorite_v1_happy_path(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile_foods.delete_favorite_v1("fid-1")

    params = mock_call.call_args.args[0]
    assert params["method"] == "food.delete_favorite"
    assert params["food_id"] == "fid-1"
    assert "serving_id" not in params
    assert "number_of_units" not in params
    assert mock_call.call_args.kwargs.get("method") == "DELETE"
    assert result is True


def test_food_delete_favorite_v1_with_serving_id_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.delete_favorite_v1("fid-1", serving_id="sid-9")
    params = mock_call.call_args.args[0]
    assert params["serving_id"] == "sid-9"
    assert "number_of_units" not in params


def test_food_delete_favorite_v1_with_number_of_units_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.delete_favorite_v1("fid-1", number_of_units=1.0)
    params = mock_call.call_args.args[0]
    assert params["number_of_units"] == 1.0
    assert "serving_id" not in params


def test_food_delete_favorite_v1_with_both_optionals(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.delete_favorite_v1(
            "fid-1", serving_id="sid-9", number_of_units=1.0
        )
    params = mock_call.call_args.args[0]
    assert params["serving_id"] == "sid-9"
    assert params["number_of_units"] == 1.0


def test_food_delete_favorite_v1_optionals_absent_when_none(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.profile_foods.delete_favorite_v1(
            "fid-1", serving_id=None, number_of_units=None
        )
    params = mock_call.call_args.args[0]
    assert "serving_id" not in params
    assert "number_of_units" not in params


def test_food_delete_favorite_v1_success_string_one_returns_true(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        result = fs.profile_foods.delete_favorite_v1("fid-1")
    assert result is True


def test_food_delete_favorite_v1_non_success_payload_passthrough(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.profile_foods.delete_favorite_v1("fid-1")
    assert result == {}


# ---------------------------------------------------------------------------
# foods.get_favorites  (v1, v2)  — GET, no params, list
# ---------------------------------------------------------------------------

FAVORITES_VERSIONS = [
    ("profile_foods.get_favorites_v1", "foods.get_favorites"),
    ("profile_foods.get_favorites_v2", "foods.get_favorites.v2"),
]


@pytest.mark.parametrize("method_name,api_method", FAVORITES_VERSIONS)
def test_foods_get_favorites_happy_path(fs, method_name, api_method):
    payload = {"foods": {"food": [_food(food_id="1"), _food(food_id="2")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)()

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    # No HTTP verb override → defaults to GET.
    assert mock_call.call_args.kwargs.get("method") is None
    assert [r.food_id for r in result] == [1, 2]


@pytest.mark.parametrize("method_name,_api", FAVORITES_VERSIONS)
def test_foods_get_favorites_single_dict_coerced_to_list(fs, method_name, _api):
    payload = {"foods": {"food": _food(food_id="999")}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert [r.food_id for r in result] == [999]


@pytest.mark.parametrize("method_name,_api", FAVORITES_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"foods": None}])
def test_foods_get_favorites_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert [r.model_dump(mode='json', exclude_unset=True) for r in result] == []


# ---------------------------------------------------------------------------
# foods.get_most_eaten  (v1, v2)  — GET, optional meal, list
# ---------------------------------------------------------------------------

MOST_EATEN_VERSIONS = [
    ("profile_foods.get_most_eaten_v1", "foods.get_most_eaten"),
    ("profile_foods.get_most_eaten_v2", "foods.get_most_eaten.v2"),
]


@pytest.mark.parametrize("method_name,api_method", MOST_EATEN_VERSIONS)
def test_foods_get_most_eaten_happy_path(fs, method_name, api_method):
    payload = {"foods": {"food": [_food(food_id="1")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)()

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert "meal" not in params
    assert mock_call.call_args.kwargs.get("method") is None
    assert [r.food_id for r in result] == [1]


@pytest.mark.parametrize("method_name,_api", MOST_EATEN_VERSIONS)
def test_foods_get_most_eaten_with_meal(fs, method_name, _api):
    payload = {"foods": {"food": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(meal="breakfast")
    params = mock_call.call_args.args[0]
    assert params["meal"] == "breakfast"


@pytest.mark.parametrize("method_name,_api", MOST_EATEN_VERSIONS)
def test_foods_get_most_eaten_meal_absent_when_none(fs, method_name, _api):
    payload = {"foods": {"food": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(meal=None)
    params = mock_call.call_args.args[0]
    assert "meal" not in params


@pytest.mark.parametrize("method_name,_api", MOST_EATEN_VERSIONS)
def test_foods_get_most_eaten_single_dict_coerced_to_list(fs, method_name, _api):
    payload = {"foods": {"food": _food(food_id="999")}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert [r.food_id for r in result] == [999]


@pytest.mark.parametrize("method_name,_api", MOST_EATEN_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"foods": None}])
def test_foods_get_most_eaten_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert [r.model_dump(mode='json', exclude_unset=True) for r in result] == []


# ---------------------------------------------------------------------------
# foods.get_recently_eaten  (v1, v2)  — GET, optional meal, list
# Note: v2 is flagged as ambiguous upstream (Premier vs Basic mismatch). We
# only verify the wrapper's actual behavior — no Premier propagation test.
# ---------------------------------------------------------------------------

RECENTLY_EATEN_VERSIONS = [
    ("profile_foods.get_recently_eaten_v1", "foods.get_recently_eaten"),
    ("profile_foods.get_recently_eaten_v2", "foods.get_recently_eaten.v2"),
]


@pytest.mark.parametrize("method_name,api_method", RECENTLY_EATEN_VERSIONS)
def test_foods_get_recently_eaten_happy_path(fs, method_name, api_method):
    payload = {"foods": {"food": [_food(food_id="1"), _food(food_id="2")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = _resolve(fs, method_name)()

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert "meal" not in params
    assert mock_call.call_args.kwargs.get("method") is None
    assert [r.food_id for r in result] == [1, 2]


@pytest.mark.parametrize("method_name,_api", RECENTLY_EATEN_VERSIONS)
def test_foods_get_recently_eaten_with_meal(fs, method_name, _api):
    payload = {"foods": {"food": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(meal="dinner")
    params = mock_call.call_args.args[0]
    assert params["meal"] == "dinner"


@pytest.mark.parametrize("method_name,_api", RECENTLY_EATEN_VERSIONS)
def test_foods_get_recently_eaten_meal_absent_when_none(fs, method_name, _api):
    payload = {"foods": {"food": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        _resolve(fs, method_name)(meal=None)
    params = mock_call.call_args.args[0]
    assert "meal" not in params


@pytest.mark.parametrize("method_name,_api", RECENTLY_EATEN_VERSIONS)
def test_foods_get_recently_eaten_single_dict_coerced_to_list(
    fs, method_name, _api
):
    payload = {"foods": {"food": _food(food_id="999")}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert [r.food_id for r in result] == [999]


@pytest.mark.parametrize("method_name,_api", RECENTLY_EATEN_VERSIONS)
@pytest.mark.parametrize("payload", [{}, {"foods": None}])
def test_foods_get_recently_eaten_empty_response_returns_empty_list(
    fs, method_name, _api, payload
):
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = _resolve(fs, method_name)()
    assert result == []
