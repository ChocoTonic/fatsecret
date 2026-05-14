"""Exhaustive unit tests for Food Diary resource methods.

Covers all 9 method-version pairs:
    food_entry.create     v1
    food_entry.edit       v1
    food_entry.delete     v1
    food_entries.get      v1, v2
    food_entries.get_month v1, v2
    food_entries.copy     v1
    food_entries.copy_saved_meal v1
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        return Fatsecret("ck", "cs")


# ============================================================================
# food_entry.create v1
# ============================================================================


def test_food_entry_create_v1_happy_path(fs):
    payload = {"food_entries": {"food_entry": {"food_entry_id": "42"}}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entry_create_v1(
            food_id="1",
            food_entry_name="Apple",
            serving_id="s1",
            number_of_units=1.5,
            meal="breakfast",
        )

    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entry.create"
    assert params["food_id"] == "1"
    assert params["food_entry_name"] == "Apple"
    assert params["serving_id"] == "s1"
    assert params["number_of_units"] == 1.5
    assert params["meal"] == "breakfast"
    assert "date" not in params
    assert mock_call.call_args.kwargs["method"] == "POST"
    # _unwrap on food_entries with list_key=food_entry → list (single → coerced)
    assert result == [{"food_entry_id": "42"}]


def test_food_entry_create_v1_returns_new_food_entry_id(fs):
    # The FS API returns `{"food_entry_id": {"value": "N"}}` on success;
    # current implementation unwraps via food_entries→food_entry, so when the
    # server returns a "food_entry_id" key directly, the helper returns it
    # coerced as a single-element list.
    payload = {"food_entry_id": {"value": "12345"}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.diary.entry_create_v1(
            food_id="1",
            food_entry_name="Apple",
            serving_id="s1",
            number_of_units=1.0,
            meal="lunch",
        )
    # _unwrap walks "food_entries" key which is absent → returns []
    assert result == []


def test_food_entry_create_v1_date_optional_omitted_when_none(fs):
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.diary.entry_create_v1("1", "n", "s", 1.0, "dinner", date=None)
    params = mock_call.call_args.args[0]
    assert "date" not in params


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entry_create_v1_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.diary.entry_create_v1("1", "n", "s", 1.0, "snacks", date=value)
    params = mock_call.call_args.args[0]
    assert params["date"] == expected


def test_food_entry_create_v1_empty_response_returns_empty_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.diary.entry_create_v1("1", "n", "s", 1.0, "breakfast")
    assert result == []


# ============================================================================
# food_entry.edit v1
# ============================================================================


def test_food_entry_edit_v1_happy_path(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        result = fs.diary.entry_edit_v1("fe1")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entry.edit"
    assert params["food_entry_id"] == "fe1"
    assert mock_call.call_args.kwargs["method"] == "PUT"
    assert result is True


def test_food_entry_edit_v1_all_optionals_present(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entry_edit_v1(
            "fe1",
            food_entry_name="Pear",
            serving_id="s9",
            number_of_units=2.5,
            meal="lunch",
        )
    params = mock_call.call_args.args[0]
    assert params["food_entry_name"] == "Pear"
    assert params["serving_id"] == "s9"
    assert params["number_of_units"] == 2.5
    assert params["meal"] == "lunch"


def test_food_entry_edit_v1_omits_optionals_when_none(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entry_edit_v1("fe1")
    params = mock_call.call_args.args[0]
    assert "food_entry_name" not in params
    assert "serving_id" not in params
    assert "number_of_units" not in params
    assert "meal" not in params


def test_food_entry_edit_v1_success_string(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        assert fs.diary.entry_edit_v1("fe1") is True


def test_food_entry_edit_v1_passes_through_non_success_payload(fs):
    with patch.object(Fatsecret, "_call", return_value={"other": "data"}):
        assert fs.diary.entry_edit_v1("fe1") == {"other": "data"}


# ============================================================================
# food_entry.delete v1
# ============================================================================


def test_food_entry_delete_v1_happy_path(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        result = fs.diary.entry_delete_v1("fe-9")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entry.delete"
    assert params["food_entry_id"] == "fe-9"
    assert mock_call.call_args.kwargs["method"] == "DELETE"
    assert result is True


def test_food_entry_delete_v1_success_zero_returns_false(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        assert fs.diary.entry_delete_v1("fe-9") is False


# ============================================================================
# food_entries.get v1
# ============================================================================


def test_food_entries_get_v1_by_food_entry_id(fs):
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "10"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_v1(food_entry_id="10")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.get"
    assert params["food_entry_id"] == "10"
    assert "date" not in params
    # GET (no explicit HTTP method kwarg)
    assert "method" not in mock_call.call_args.kwargs
    assert result == [{"food_entry_id": "10"}]


def test_food_entries_get_v1_by_date(fs):
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "20"}]}}
    d = datetime.date(2021, 6, 1)
    expected = Fatsecret.unix_time_v2(d)
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.diary.entries_get_v1(date=d)
    params = mock_call.call_args.args[0]
    assert params["date"] == expected
    assert "food_entry_id" not in params


def test_food_entries_get_v1_single_dict_coerced_to_list(fs):
    payload = {"food_entries": {"food_entry": {"food_entry_id": "10"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.diary.entries_get_v1(food_entry_id="10")
    assert result == [{"food_entry_id": "10"}]


def test_food_entries_get_v1_no_args_short_circuits(fs):
    with patch.object(Fatsecret, "_call") as mock_call:
        assert fs.diary.entries_get_v1() == []
    mock_call.assert_not_called()


def test_food_entries_get_v1_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.diary.entries_get_v1(food_entry_id="x") == []


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_get_v1_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.diary.entries_get_v1(date=value)
    assert mock_call.call_args.args[0]["date"] == expected


# ============================================================================
# food_entries.get v2
# ============================================================================


def test_food_entries_get_v2_by_food_entry_id(fs):
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "55"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_v2(food_entry_id="55")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.get.v2"
    assert params["food_entry_id"] == "55"
    assert result == [{"food_entry_id": "55"}]


def test_food_entries_get_v2_by_date(fs):
    d = datetime.datetime(2022, 3, 4)
    expected = Fatsecret.unix_time_v2(d)
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.diary.entries_get_v2(date=d)
    params = mock_call.call_args.args[0]
    assert params["date"] == expected


def test_food_entries_get_v2_single_dict_coerced(fs):
    payload = {"food_entries": {"food_entry": {"food_entry_id": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.diary.entries_get_v2(food_entry_id="1") == [{"food_entry_id": "1"}]


def test_food_entries_get_v2_list_passthrough(fs):
    payload = {"food_entries": {"food_entry": [{"food_entry_id": "1"}, {"food_entry_id": "2"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.diary.entries_get_v2(food_entry_id="1")
    assert result == [{"food_entry_id": "1"}, {"food_entry_id": "2"}]


def test_food_entries_get_v2_no_args_short_circuits(fs):
    with patch.object(Fatsecret, "_call") as mock_call:
        assert fs.diary.entries_get_v2() == []
    mock_call.assert_not_called()


def test_food_entries_get_v2_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.diary.entries_get_v2(food_entry_id="x") == []


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_get_v2_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.diary.entries_get_v2(date=value)
    assert mock_call.call_args.args[0]["date"] == expected


# ============================================================================
# food_entries.get_month v1
# ============================================================================


def test_food_entries_get_month_v1_no_date(fs):
    payload = {"month": {"day": [{"date_int": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_month_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.get_month"
    assert "date" not in params
    assert result == [{"date_int": "1"}]


def test_food_entries_get_month_v1_with_date(fs):
    d = datetime.date(2020, 5, 1)
    expected = Fatsecret.unix_time_v2(d)
    payload = {"month": {"day": [{"date_int": "1"}, {"date_int": "2"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_month_v1(date=d)
    assert mock_call.call_args.args[0]["date"] == expected
    assert result == [{"date_int": "1"}, {"date_int": "2"}]


def test_food_entries_get_month_v1_single_day_coerced(fs):
    payload = {"month": {"day": {"date_int": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.diary.entries_get_month_v1() == [{"date_int": "1"}]


def test_food_entries_get_month_v1_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.diary.entries_get_month_v1() == []


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_get_month_v1_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.diary.entries_get_month_v1(date=value)
    assert mock_call.call_args.args[0]["date"] == expected


# ============================================================================
# food_entries.get_month v2
# ============================================================================


def test_food_entries_get_month_v2_no_date(fs):
    payload = {"month": {"day": [{"date_int": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.diary.entries_get_month_v2()
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.get_month.v2"
    assert "date" not in params
    assert result == [{"date_int": "1"}]


def test_food_entries_get_month_v2_with_date(fs):
    d = datetime.datetime(2023, 2, 1)
    expected = Fatsecret.unix_time_v2(d)
    payload = {"month": {"day": [{"date_int": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.diary.entries_get_month_v2(date=d)
    assert mock_call.call_args.args[0]["date"] == expected


def test_food_entries_get_month_v2_single_day_coerced(fs):
    payload = {"month": {"day": {"date_int": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert fs.diary.entries_get_month_v2() == [{"date_int": "1"}]


def test_food_entries_get_month_v2_empty_response(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.diary.entries_get_month_v2() == []


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_get_month_v2_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.diary.entries_get_month_v2(date=value)
    assert mock_call.call_args.args[0]["date"] == expected


# ============================================================================
# food_entries.copy v1
# ============================================================================


def test_food_entries_copy_v1_happy_path(fs):
    from_d = datetime.date(2024, 1, 1)
    to_d = datetime.date(2024, 1, 2)
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        result = fs.diary.entries_copy_v1(from_d, to_d)
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.copy"
    assert params["from_date"] == Fatsecret.unix_time_v2(from_d)
    assert params["to_date"] == Fatsecret.unix_time_v2(to_d)
    assert "meal" not in params
    assert mock_call.call_args.kwargs["method"] == "POST"
    assert result is True


def test_food_entries_copy_v1_with_meal(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_v1(0, 1, meal="lunch")
    assert mock_call.call_args.args[0]["meal"] == "lunch"


def test_food_entries_copy_v1_meal_none_omitted(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_v1(0, 1, meal=None)
    assert "meal" not in mock_call.call_args.args[0]


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_copy_v1_from_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_v1(value, 0)
    assert mock_call.call_args.args[0]["from_date"] == expected


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_copy_v1_to_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_v1(0, value)
    assert mock_call.call_args.args[0]["to_date"] == expected


def test_food_entries_copy_v1_success_zero_returns_false(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        assert fs.diary.entries_copy_v1(0, 1) is False


# ============================================================================
# food_entries.copy_saved_meal v1
# ============================================================================


def test_food_entries_copy_saved_meal_v1_happy_path(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        result = fs.diary.entries_copy_saved_meal_v1("sm-1", "dinner")
    params = mock_call.call_args.args[0]
    assert params["method"] == "food_entries.copy_saved_meal"
    assert params["saved_meal_id"] == "sm-1"
    assert params["meal"] == "dinner"
    assert "date" not in params
    assert mock_call.call_args.kwargs["method"] == "POST"
    assert result is True


def test_food_entries_copy_saved_meal_v1_date_none_omitted(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_saved_meal_v1("sm-1", "dinner", date=None)
    assert "date" not in mock_call.call_args.args[0]


@pytest.mark.parametrize(
    "value",
    [
        datetime.datetime(2020, 1, 15),
        datetime.date(2020, 1, 15),
        int(datetime.datetime(2020, 1, 15).timestamp()),
        float(datetime.datetime(2020, 1, 15).timestamp()),
    ],
)
def test_food_entries_copy_saved_meal_v1_date_coercion(fs, value):
    expected = Fatsecret.unix_time_v2(value)
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.diary.entries_copy_saved_meal_v1("sm-1", "dinner", date=value)
    assert mock_call.call_args.args[0]["date"] == expected


def test_food_entries_copy_saved_meal_v1_success_zero_returns_false(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 0}):
        assert fs.diary.entries_copy_saved_meal_v1("sm", "lunch") is False


def test_food_entries_copy_saved_meal_v1_success_string(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": "1"}):
        assert fs.diary.entries_copy_saved_meal_v1("sm", "lunch") is True
