"""Exhaustive unit tests for Weight + Profile resource wrappers.

Covers:
  - weight.update_v1
  - weight.get_month_v1, _v2
  - profile.create_v1
  - profile.get_v1
  - profile.get_auth_v1
"""

import datetime
from unittest.mock import patch

import pytest

from fatsecret import Fatsecret

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


# --------------------------- weight.update v1 ---------------------------


def test_weight_update_v1_minimal_required(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.weight.update_v1(70.5)
    params = mock_call.call_args.args[0]
    assert params["method"] == "weight.update"
    assert params["current_weight_kg"] == 70.5
    # No optionals when not supplied
    assert "weight_type" not in params
    assert "height_type" not in params
    assert "goal_weight_kg" not in params
    assert "current_height_cm" not in params
    assert "comment" not in params
    assert "date" not in params
    # POST verb
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_weight_update_v1_success_string_one(fs):
    """_mutator_success should also accept the string '1'."""
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        assert fs.weight.update_v1(70.0) is True


def test_weight_update_v1_success_zero_is_false(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        assert fs.weight.update_v1(70.0) is False


def test_weight_update_v1_all_optional_params(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.weight.update_v1(
            72.0,
            weight_type="kg",
            height_type="cm",
            goal_weight_kg=68.0,
            current_height_cm=175.0,
            comment="hello",
        )
    params = mock_call.call_args.args[0]
    assert params["weight_type"] == "kg"
    assert params["height_type"] == "cm"
    assert params["goal_weight_kg"] == 68.0
    assert params["current_height_cm"] == 175.0
    assert params["comment"] == "hello"


def test_weight_update_v1_first_weighin_requires_goal_and_height(fs):
    """The first weigh-in requires goal_weight_kg and current_height_cm.

    Wrapper must accept and forward both.
    """
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.weight.update_v1(70.0, goal_weight_kg=65.0, current_height_cm=180.0)
    params = mock_call.call_args.args[0]
    assert params["goal_weight_kg"] == 65.0
    assert params["current_height_cm"] == 180.0


@pytest.mark.parametrize(
    "date_in",
    [
        datetime.datetime(2024, 1, 15),
        datetime.date(2024, 1, 15),
        1705276800,  # int unix timestamp
        1705276800.0,  # float unix timestamp
    ],
)
def test_weight_update_v1_date_coercion_accepts_all_types(fs, date_in):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.weight.update_v1(70.0, date=date_in)
    params = mock_call.call_args.args[0]
    assert "date" in params
    # unix_time_v2 returns days since epoch (int)
    assert isinstance(params["date"], int)


def test_weight_update_v1_date_none_omitted(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.weight.update_v1(70.0, date=None)
    params = mock_call.call_args.args[0]
    assert "date" not in params


# --------------------------- weights.get_month v1 ---------------------------


def _month_payload(days):
    return {"month": {"day": days}}


def test_weights_get_month_v1_method_and_no_date(fs):
    payload = _month_payload([{"date_int": "20000", "weight_kg": "70"}])
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.weight.get_month_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "weights.get_month"
    assert "date" not in params
    # GET verb (no `method=` kwarg means default GET path)
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert [r.date_int for r in result] == [20000]


def test_weights_get_month_v1_single_dict_coerced_to_list(fs):
    payload = _month_payload({"date_int": "20000", "weight_kg": "70"})
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.weight.get_month_v1()
    assert [r.date_int for r in result] == [20000]


def test_weights_get_month_v1_list_passthrough(fs):
    days = [{"date_int": "20000"}, {"date_int": "20001"}]
    with patch.object(Fatsecret, "_call", return_value=_month_payload(days)):
        result = fs.weight.get_month_v1()
    assert [d.date_int for d in result] == [int(x["date_int"]) for x in days]


def test_weights_get_month_v1_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={"month": None}):
        result = fs.weight.get_month_v1()
    assert [r.model_dump(mode="json", exclude_unset=True) for r in result] == []


@pytest.mark.parametrize(
    "date_in",
    [
        datetime.datetime(2024, 1, 15),
        datetime.date(2024, 1, 15),
        1705276800,
        1705276800.0,
    ],
)
def test_weights_get_month_v1_date_coercion(fs, date_in):
    with patch.object(Fatsecret, "_call", return_value=_month_payload([])) as mock_call:
        fs.weight.get_month_v1(date=date_in)
    params = mock_call.call_args.args[0]
    assert isinstance(params["date"], int)


# --------------------------- weights.get_month v2 ---------------------------


def test_weights_get_month_v2_method_name(fs):
    with patch.object(Fatsecret, "_call", return_value=_month_payload([])) as mock_call:
        result = fs.weight.get_month_v2()
    params = mock_call.call_args.args[0]
    assert params["method"] == "weights.get_month.v2"
    assert [r.model_dump(mode="json", exclude_unset=True) for r in result] == []


def test_weights_get_month_v2_single_dict_coerced(fs):
    payload = _month_payload({"date_int": "20100", "weight_kg": "68"})
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.weight.get_month_v2()
    assert len(result) == 1
    assert result[0].date_int == 20100


def test_weights_get_month_v2_list_passthrough(fs):
    days = [{"date_int": "20100"}, {"date_int": "20101"}]
    with patch.object(Fatsecret, "_call", return_value=_month_payload(days)):
        result = fs.weight.get_month_v2()
    assert [d.date_int for d in result] == [int(x["date_int"]) for x in days]


def test_weights_get_month_v2_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={"month": None}):
        assert fs.weight.get_month_v2() == []


@pytest.mark.parametrize(
    "date_in",
    [
        datetime.datetime(2024, 6, 1),
        datetime.date(2024, 6, 1),
        1717200000,
        1717200000.0,
    ],
)
def test_weights_get_month_v2_date_coercion(fs, date_in):
    with patch.object(Fatsecret, "_call", return_value=_month_payload([])) as mock_call:
        fs.weight.get_month_v2(date=date_in)
    params = mock_call.call_args.args[0]
    assert isinstance(params["date"], int)


# --------------------------- profile.create v1 ---------------------------


def test_profile_create_v1_with_user_id(fs):
    payload = {"profile": {"auth_token": "t2", "auth_secret": "s2"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile.create_v1(user_id="user-42")
    params = mock_call.call_args.args[0]
    assert params["method"] == "profile.create"
    assert params["user_id"] == "user-42"
    assert mock_call.call_args.kwargs.get("method") == "POST"
    # v2.0: returns the unwrapped profile dict (no more tuple coercion).
    # Phase 2: result is now Profile typed model
    from fatsecret.models import Profile

    assert isinstance(result, Profile)
    _dump = result.model_dump(exclude_unset=True)

    assert _dump == {"auth_token": "t2", "auth_secret": "s2"}


def test_profile_create_v1_returns_profile_dict_passthrough(fs):
    """If the response lacks auth_token, the profile dict is returned as-is."""
    payload = {"profile": {"some_other_field": "x"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.profile.create_v1(user_id="user-42")
    _dump = result.model_dump(exclude_unset=True)

    assert _dump == {"some_other_field": "x"}


# --------------------------- profile.get v1 ---------------------------


def test_profile_get_v1_returns_profile_dict(fs):
    payload = {
        "profile": {
            "nickname": "alice",
            "is_premier": "false",
            "last_weight_date_int": 20000,  # Pydantic coerces,
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile.get_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "profile.get"
    # No POST kwarg => default GET path
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert result.model_dump(exclude_unset=True, exclude_none=True) == {
        "nickname": "alice",
        "is_premier": "false",
        "last_weight_date_int": 20000,  # Pydantic coerces,
    }
    # Phase 2: result is now Profile typed model
    from fatsecret.models import Profile

    assert isinstance(result, Profile)


def test_profile_get_v1_no_arguments(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"profile": {"nickname": "n"}}
    ) as mock_call:
        fs.profile.get_v1()
    params = mock_call.call_args.args[0]
    # Only method key
    assert list(params.keys()) == ["method"]


# --------------------------- profile.get_auth v1 ---------------------------


def test_profile_get_auth_v1_returns_profile_dict(fs):
    payload = {"profile": {"auth_token": "atk", "auth_secret": "ask"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile.get_auth_v1(user_id="user-7")
    params = mock_call.call_args.args[0]
    assert params["method"] == "profile.get_auth"
    assert params["user_id"] == "user-7"
    # default verb (GET)
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    # v2.0: returns the unwrapped profile dict (no more tuple coercion).
    # Phase 2: result is now Profile typed model
    from fatsecret.models import Profile

    assert isinstance(result, Profile)
    _dump = result.model_dump(exclude_unset=True)

    assert _dump == {"auth_token": "atk", "auth_secret": "ask"}
    assert result.auth_token is not None and result.auth_secret is not None


def test_profile_get_auth_v1_without_user_id(fs):
    payload = {"profile": {"auth_token": "a", "auth_secret": "b"}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.profile.get_auth_v1()
    params = mock_call.call_args.args[0]
    assert "user_id" not in params
    _dump = result.model_dump(exclude_unset=True)

    assert _dump == {"auth_token": "a", "auth_secret": "b"}


def test_profile_get_auth_v1_without_auth_token_passes_through(fs):
    """Profile dict without auth_token is still returned verbatim."""
    payload = {"profile": {"nickname": "noauth"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.profile.get_auth_v1(user_id="u")
    _dump = result.model_dump(exclude_unset=True)

    assert _dump == {"nickname": "noauth"}
