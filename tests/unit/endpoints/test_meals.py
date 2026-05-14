"""Exhaustive unit tests for the Saved Meals resource.

Covers the ten method-version pairs (all Premier-only):
  * saved_meal.create        v1
  * saved_meal.edit          v1
  * saved_meal.delete        v1
  * saved_meals.get          v1, v2
  * saved_meal_item.add      v1
  * saved_meal_item.edit     v1
  * saved_meal_item.delete   v1
  * saved_meal_items.get     v1, v2

For each method-version we assert:
  1. Happy path: correct ``method=`` value and HTTP verb to ``_call``.
  2. Required params propagated.
  3. Optional params: present when supplied, absent when None.
  4. Mutators returning ``{"success": 1}`` collapsed to ``True``.
  5. ``saved_meal.create`` / ``saved_meal_item.add`` IDs unwrapped.
  6. Get-list endpoints: single-dict coerced, list passed through, empty → [].
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        return Fatsecret("ck", "cs")


# ---------------------------------------------------------------------------
# saved_meal.create v1
# ---------------------------------------------------------------------------


def test_saved_meal_create_v1_happy_path(fs):
    payload = {"saved_meal_id": {"value": "12345"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.saved_meal_create_v1("My Lunch")

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal.create"
    assert params["saved_meal_name"] == "My Lunch"
    # Optionals omitted when None.
    assert "saved_meal_description" not in params
    assert "meals" not in params
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result == {"value": "12345"}


def test_saved_meal_create_v1_with_all_optionals(fs):
    payload = {"saved_meal_id": "999"}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.saved_meal_create_v1(
            "Dinner",
            saved_meal_description="A tasty dinner",
            meals="breakfast,lunch",
        )

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal.create"
    assert params["saved_meal_name"] == "Dinner"
    assert params["saved_meal_description"] == "A tasty dinner"
    # `meals` is documented as a string in v1 — pass-through, no list-join.
    assert params["meals"] == "breakfast,lunch"
    assert result == "999"


def test_saved_meal_create_v1_meals_is_passthrough_string(fs):
    """v1 wrapper does NOT mutate `meals`; the legacy alias joined lists."""
    payload = {"saved_meal_id": "1"}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.saved_meal_create_v1("name", meals="breakfast")

    params = mock_call.call_args.args[0]
    assert params["meals"] == "breakfast"
    assert isinstance(params["meals"], str)


def test_saved_meal_create_v1_empty_response(fs):
    # `_unwrap` for a scalar key returns None when the key is missing.
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.saved_meal_create_v1("name")
    assert result is None


# ---------------------------------------------------------------------------
# saved_meal.edit v1
# ---------------------------------------------------------------------------


def test_saved_meal_edit_v1_happy_path(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_edit_v1("123")

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal.edit"
    assert params["saved_meal_id"] == "123"
    assert "saved_meal_name" not in params
    assert "saved_meal_description" not in params
    assert "meals" not in params
    assert mock_call.call_args.kwargs.get("method") == "PUT"
    assert result is True


def test_saved_meal_edit_v1_with_all_optionals(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_edit_v1(
            "123",
            saved_meal_name="Renamed",
            saved_meal_description="updated desc",
            meals="dinner",
        )

    params = mock_call.call_args.args[0]
    assert params["saved_meal_name"] == "Renamed"
    assert params["saved_meal_description"] == "updated desc"
    assert params["meals"] == "dinner"
    assert result is True


def test_saved_meal_edit_v1_success_string_one_also_true(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        result = fs.saved_meal_edit_v1("123")
    assert result is True


def test_saved_meal_edit_v1_non_success_payload_passthrough(fs):
    payload = {"error": "something"}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.saved_meal_edit_v1("123")
    assert result == payload


# ---------------------------------------------------------------------------
# saved_meal.delete v1
# ---------------------------------------------------------------------------


def test_saved_meal_delete_v1_happy_path(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_delete_v1("123")

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal.delete"
    assert params["saved_meal_id"] == "123"
    assert mock_call.call_args.kwargs.get("method") == "DELETE"
    assert result is True


def test_saved_meal_delete_v1_failure_passthrough(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        result = fs.saved_meal_delete_v1("123")
    assert result is False


# ---------------------------------------------------------------------------
# saved_meals.get  (v1, v2)
# ---------------------------------------------------------------------------

SAVED_MEALS_GET_VERSIONS = [
    ("saved_meals_get_v1", "saved_meals.get"),
    ("saved_meals_get_v2", "saved_meals.get.v2"),
]


@pytest.mark.parametrize("method_name,api_method", SAVED_MEALS_GET_VERSIONS)
def test_saved_meals_get_happy_path(fs, method_name, api_method):
    payload = {
        "saved_meals": {
            "saved_meal": [
                {"saved_meal_id": "1", "saved_meal_name": "Lunch"},
                {"saved_meal_id": "2", "saved_meal_name": "Dinner"},
            ]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs, method_name)()

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert "meal" not in params
    # HTTP verb defaults to GET (no `method=` kwarg passed).
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert result == [
        {"saved_meal_id": "1", "saved_meal_name": "Lunch"},
        {"saved_meal_id": "2", "saved_meal_name": "Dinner"},
    ]


@pytest.mark.parametrize("method_name,api_method", SAVED_MEALS_GET_VERSIONS)
def test_saved_meals_get_with_meal_filter(fs, method_name, api_method):
    payload = {"saved_meals": {"saved_meal": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs, method_name)(meal="breakfast")

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["meal"] == "breakfast"
    assert result == []


@pytest.mark.parametrize("method_name,_", SAVED_MEALS_GET_VERSIONS)
def test_saved_meals_get_single_dict_coerced(fs, method_name, _):
    payload = {"saved_meals": {"saved_meal": {"saved_meal_id": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = getattr(fs, method_name)()
    assert result == [{"saved_meal_id": "1"}]


@pytest.mark.parametrize("method_name,_", SAVED_MEALS_GET_VERSIONS)
def test_saved_meals_get_empty_response(fs, method_name, _):
    # No `saved_meals` key at all → unwrap returns [].
    with patch.object(Fatsecret, "_call", return_value={}):
        result = getattr(fs, method_name)()
    assert result == []


@pytest.mark.parametrize("method_name,_", SAVED_MEALS_GET_VERSIONS)
def test_saved_meals_get_null_inner_response(fs, method_name, _):
    with patch.object(
        Fatsecret, "_call", return_value={"saved_meals": None}
    ):
        result = getattr(fs, method_name)()
    assert result == []


# ---------------------------------------------------------------------------
# saved_meal_item.add v1
# ---------------------------------------------------------------------------


def test_saved_meal_item_add_v1_happy_path(fs):
    payload = {"saved_meal_item_id": "77"}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.saved_meal_item_add_v1(
            saved_meal_id="10",
            food_id="200",
            saved_meal_item_name="Apple",
            serving_id="3",
            number_of_units=1.5,
        )

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal_item.add"
    assert params["saved_meal_id"] == "10"
    assert params["food_id"] == "200"
    assert params["saved_meal_item_name"] == "Apple"
    assert params["serving_id"] == "3"
    assert params["number_of_units"] == 1.5
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result == "77"


def test_saved_meal_item_add_v1_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.saved_meal_item_add_v1("1", "2", "n", "3", 1.0)
    assert result is None


# ---------------------------------------------------------------------------
# saved_meal_item.edit v1
# ---------------------------------------------------------------------------


def test_saved_meal_item_edit_v1_happy_path(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_item_edit_v1("77")

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal_item.edit"
    assert params["saved_meal_item_id"] == "77"
    assert "saved_meal_item_name" not in params
    assert "number_of_units" not in params
    assert mock_call.call_args.kwargs.get("method") == "PUT"
    assert result is True


def test_saved_meal_item_edit_v1_with_all_optionals(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_item_edit_v1(
            "77",
            saved_meal_item_name="Renamed Apple",
            number_of_units=2.0,
        )

    params = mock_call.call_args.args[0]
    assert params["saved_meal_item_name"] == "Renamed Apple"
    assert params["number_of_units"] == 2.0
    assert result is True


def test_saved_meal_item_edit_v1_cannot_change_serving_id(fs):
    """Per the YAML spec, ``serving_id`` is NOT an editable param.

    The wrapper signature must not accept it as a keyword argument.
    The namespaced method on ``meals`` holds the real signature; the
    flat ``Fatsecret.saved_meal_item_edit_v1`` is a deprecation alias
    using ``*args, **kwargs``.
    """
    import inspect

    sig = inspect.signature(fs.meals.item_edit_v1)
    assert "serving_id" not in sig.parameters
    # Documented editable params are present:
    assert "saved_meal_item_id" in sig.parameters
    assert "saved_meal_item_name" in sig.parameters
    assert "number_of_units" in sig.parameters


def test_saved_meal_item_edit_v1_partial_optional_only_name(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        fs.saved_meal_item_edit_v1("77", saved_meal_item_name="x")

    params = mock_call.call_args.args[0]
    assert params["saved_meal_item_name"] == "x"
    assert "number_of_units" not in params


# ---------------------------------------------------------------------------
# saved_meal_item.delete v1
# ---------------------------------------------------------------------------


def test_saved_meal_item_delete_v1_happy_path(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"success": 1}
    ) as mock_call:
        result = fs.saved_meal_item_delete_v1("77")

    params = mock_call.call_args.args[0]
    assert params["method"] == "saved_meal_item.delete"
    assert params["saved_meal_item_id"] == "77"
    assert mock_call.call_args.kwargs.get("method") == "DELETE"
    assert result is True


def test_saved_meal_item_delete_v1_failure_passthrough(fs):
    payload = {"success": 0}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.saved_meal_item_delete_v1("77")
    assert result is False


# ---------------------------------------------------------------------------
# saved_meal_items.get  (v1, v2)
# ---------------------------------------------------------------------------

SAVED_MEAL_ITEMS_GET_VERSIONS = [
    ("saved_meal_items_get_v1", "saved_meal_items.get"),
    ("saved_meal_items_get_v2", "saved_meal_items.get.v2"),
]


@pytest.mark.parametrize(
    "method_name,api_method", SAVED_MEAL_ITEMS_GET_VERSIONS
)
def test_saved_meal_items_get_happy_path(fs, method_name, api_method):
    payload = {
        "saved_meal_items": {
            "saved_meal_item": [
                {"saved_meal_item_id": "1"},
                {"saved_meal_item_id": "2"},
            ]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs, method_name)("10")

    params = mock_call.call_args.args[0]
    assert params["method"] == api_method
    assert params["saved_meal_id"] == "10"
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert result == [
        {"saved_meal_item_id": "1"},
        {"saved_meal_item_id": "2"},
    ]


@pytest.mark.parametrize("method_name,_", SAVED_MEAL_ITEMS_GET_VERSIONS)
def test_saved_meal_items_get_single_dict_coerced(fs, method_name, _):
    payload = {
        "saved_meal_items": {"saved_meal_item": {"saved_meal_item_id": "1"}}
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = getattr(fs, method_name)("10")
    assert result == [{"saved_meal_item_id": "1"}]


@pytest.mark.parametrize("method_name,_", SAVED_MEAL_ITEMS_GET_VERSIONS)
def test_saved_meal_items_get_empty_response(fs, method_name, _):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = getattr(fs, method_name)("10")
    assert result == []


@pytest.mark.parametrize("method_name,_", SAVED_MEAL_ITEMS_GET_VERSIONS)
def test_saved_meal_items_get_null_inner_response(fs, method_name, _):
    with patch.object(
        Fatsecret, "_call", return_value={"saved_meal_items": None}
    ):
        result = getattr(fs, method_name)("10")
    assert result == []
