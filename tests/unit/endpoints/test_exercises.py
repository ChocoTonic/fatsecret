"""Exhaustive unit tests for the Exercise resource (9 method-version pairs).

Covers:
- exercises.get v1, v2
- exercise_entries.get v1, v2
- exercise_entries.get_month v1, v2
- exercise_entry.edit v1
- exercise_entries.commit_day v1
- exercise_entries.save_template v1
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


# Reference date: 2021-06-15 -> 18793 days since epoch.
REF_DT = datetime.datetime(2021, 6, 15)
REF_DATE = datetime.date(2021, 6, 15)
REF_TS = int(REF_DT.replace(tzinfo=datetime.timezone.utc).timestamp())
REF_DAYS = (REF_DT - datetime.datetime(1970, 1, 1)).days


# --------------------------- exercises.get v1 / v2 ---------------------------


def test_exercises_get_v1_happy_path_minimal(fs):
    payload = {"exercise_types": {"exercise": [_exercise(exercise_name="Running")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.list_v1()

    params = mock_call.call_args.args[0]
    assert params["method"] == "exercises.get"
    # GET is the default in _call -> no `method=` kwarg expected.
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert "region" not in params and "language" not in params
    assert [r.exercise_name for r in result] == ["Running"]


def test_exercises_get_v1_premier_params_propagated(fs):
    """exercises.get carries the Premier-exclusive region/language params."""
    payload = {"exercise_types": {"exercise": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.exercises.list_v1(region="US", language="en")
    params = mock_call.call_args.args[0]
    assert params["region"] == "US"
    assert params["language"] == "en"


def test_exercises_get_v1_single_dict_coerced_to_list(fs):
    payload = {"exercise_types": {"exercise": _exercise(exercise_name="Running")}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.exercises.list_v1()
    assert [r.exercise_name for r in result] == ["Running"]


def test_exercises_get_v1_empty_returns_empty_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        result = fs.exercises.list_v1()
    assert [r.model_dump(mode="json", exclude_unset=True) for r in result] == []


def test_exercises_get_v2_happy_path(fs):
    payload = {"exercise_types": {"exercise": [_exercise(exercise_name="Cycling")]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.list_v2()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercises.get.v2"
    assert "region" not in params and "language" not in params
    assert [r.exercise_name for r in result] == ["Cycling"]


def test_exercises_get_v2_premier_params_propagated(fs):
    payload = {"exercise_types": {"exercise": []}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.exercises.list_v2(region="GB", language="fr")
    params = mock_call.call_args.args[0]
    assert params["region"] == "GB"
    assert params["language"] == "fr"


def test_exercises_get_v2_empty_returns_empty_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.exercises.list_v2() == []


# --------------------------- exercise_entries.get v1 / v2 ---------------------------


def _date_calls_identical(fs, fn):
    """Helper: assert datetime/date/int/float produce the same params."""
    results = []
    for d in (REF_DT, REF_DATE, REF_TS, float(REF_TS)):
        with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
            fn(date=d)
        results.append(mock_call.call_args.args[0])
    # All must be equal
    for r in results[1:]:
        assert r == results[0]
    # And date must equal REF_DAYS
    assert results[0]["date"] == REF_DAYS


def test_exercise_entries_get_v1_happy_path_no_date(fs):
    payload = {
        "exercise_entries": {"exercise_entry": [_exercise_entry(exercise_entry_id="1")]}
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_get_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entries.get"
    assert "date" not in params
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert [r.exercise_entry_id for r in result] == ["1"]


def test_exercise_entries_get_v1_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.exercises.entries_get_v1(date=REF_DT)
    params = mock_call.call_args.args[0]
    assert params["date"] == REF_DAYS


def test_exercise_entries_get_v1_date_coercion(fs):
    _date_calls_identical(fs, fs.exercises.entries_get_v1)


def test_exercise_entries_get_v1_single_dict_coerced(fs):
    payload = {
        "exercise_entries": {"exercise_entry": _exercise_entry(exercise_entry_id="9")}
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.exercises.entries_get_v1()
    assert [r.exercise_entry_id for r in result] == ["9"]


def test_exercise_entries_get_v1_empty_returns_empty_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.exercises.entries_get_v1() == []


def test_exercise_entries_get_v2_happy_path(fs):
    payload = {
        "exercise_entries": {
            "exercise_entry": [
                _exercise_entry(exercise_entry_id="1"),
                _exercise_entry(exercise_entry_id="2"),
            ]
        }
    }
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_get_v2()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entries.get.v2"
    assert "date" not in params
    assert [r.exercise_entry_id for r in result] == ["1", "2"]


def test_exercise_entries_get_v2_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.exercises.entries_get_v2(date=REF_DATE)
    params = mock_call.call_args.args[0]
    assert params["date"] == REF_DAYS


def test_exercise_entries_get_v2_date_coercion(fs):
    _date_calls_identical(fs, fs.exercises.entries_get_v2)


def test_exercise_entries_get_v2_single_dict_coerced(fs):
    payload = {
        "exercise_entries": {"exercise_entry": _exercise_entry(exercise_entry_id="9")}
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert [r.exercise_entry_id for r in fs.exercises.entries_get_v2()] == ["9"]


def test_exercise_entries_get_v2_empty_returns_empty_list(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.exercises.entries_get_v2() == []


# --------------------------- exercise_entries.get_month v1 / v2 ---------------------------


def test_exercise_entries_get_month_v1_happy_path_no_date(fs):
    payload = {"month": {"day": [{"date_int": "1"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_get_month_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entries.get_month"
    assert "date" not in params
    assert mock_call.call_args.kwargs.get("method") in (None, "GET")
    assert [r.date_int for r in result] == [1]


def test_exercise_entries_get_month_v1_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.exercises.entries_get_month_v1(date=REF_DT)
    assert mock_call.call_args.args[0]["date"] == REF_DAYS


def test_exercise_entries_get_month_v1_date_coercion(fs):
    _date_calls_identical(fs, fs.exercises.entries_get_month_v1)


def test_exercise_entries_get_month_v1_single_day_coerced(fs):
    payload = {"month": {"day": {"date_int": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert [r.date_int for r in fs.exercises.entries_get_month_v1()] == [1]


def test_exercise_entries_get_month_v1_empty_returns_empty(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.exercises.entries_get_month_v1() == []


def test_exercise_entries_get_month_v2_happy_path(fs):
    payload = {"month": {"day": [{"date_int": "1"}, {"date_int": "2"}]}}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_get_month_v2()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entries.get_month.v2"
    assert "date" not in params
    assert [r.date_int for r in result] == [1, 2]


def test_exercise_entries_get_month_v2_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={}) as mock_call:
        fs.exercises.entries_get_month_v2(date=REF_DATE)
    assert mock_call.call_args.args[0]["date"] == REF_DAYS


def test_exercise_entries_get_month_v2_date_coercion(fs):
    _date_calls_identical(fs, fs.exercises.entries_get_month_v2)


def test_exercise_entries_get_month_v2_single_day_coerced(fs):
    payload = {"month": {"day": {"date_int": "1"}}}
    with patch.object(Fatsecret, "_call", return_value=payload):
        assert [r.date_int for r in fs.exercises.entries_get_month_v2()] == [1]


def test_exercise_entries_get_month_v2_empty_returns_empty(fs):
    with patch.object(Fatsecret, "_call", return_value={}):
        assert fs.exercises.entries_get_month_v2() == []


# --------------------------- exercise_entry.edit v1 ---------------------------


def test_exercise_entry_edit_v1_happy_path_required_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entry_edit_v1(
            shift_to_id="11", shift_from_id="22", minutes=30
        )
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entry.edit"
    assert params["shift_to_id"] == "11"
    assert params["shift_from_id"] == "22"
    assert params["minutes"] == 30
    # Optional params absent when not supplied
    for key in ("date", "shift_to_name", "shift_from_name", "kcal"):
        assert key not in params
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_exercise_entry_edit_v1_all_optional_params_present(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.exercises.entry_edit_v1(
            shift_to_id="11",
            shift_from_id="22",
            minutes=15,
            date=REF_DT,
            shift_to_name="Running",
            shift_from_name="Walking",
            kcal=250,
        )
    params = mock_call.call_args.args[0]
    assert params["date"] == REF_DAYS
    assert params["shift_to_name"] == "Running"
    assert params["shift_from_name"] == "Walking"
    assert params["kcal"] == 250


def test_exercise_entry_edit_v1_date_coercion(fs):
    results = []
    for d in (REF_DT, REF_DATE, REF_TS, float(REF_TS)):
        with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
            fs.exercises.entry_edit_v1(
                shift_to_id="11", shift_from_id="22", minutes=10, date=d
            )
        results.append(mock_call.call_args.args[0])
    for r in results[1:]:
        assert r == results[0]
    assert results[0]["date"] == REF_DAYS


def test_exercise_entry_edit_v1_mutator_returns_true(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}):
        assert (
            fs.exercises.entry_edit_v1(shift_to_id="1", shift_from_id="2", minutes=5)
            is True
        )


# --------------------------- exercise_entries.commit_day v1 ---------------------------


def test_exercise_entries_commit_day_v1_happy_path_no_date(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_commit_day_v1()
    params = mock_call.call_args.args[0]
    assert params["method"] == "exercise_entries.commit_day"
    assert "date" not in params
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_exercise_entries_commit_day_v1_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.exercises.entries_commit_day_v1(date=REF_DT)
    assert mock_call.call_args.args[0]["date"] == REF_DAYS


def test_exercise_entries_commit_day_v1_date_coercion(fs):
    results = []
    for d in (REF_DT, REF_DATE, REF_TS, float(REF_TS)):
        with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
            fs.exercises.entries_commit_day_v1(date=d)
        results.append(mock_call.call_args.args[0])
    for r in results[1:]:
        assert r == results[0]
    assert results[0]["date"] == REF_DAYS


def test_exercise_entries_commit_day_v1_mutator_returns_true(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}):
        assert fs.exercises.entries_commit_day_v1() is True


# --------------------------- exercise_entries.save_template v1 ---------------------------


def test_exercise_entries_save_template_v1_happy_path_required_only(fs):
    payload = {"success": 1}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.exercises.entries_save_template_v1(days=3)
    params = mock_call.call_args.args[0]
    # Critical: assert the legacy copy/paste bug is fixed.
    assert params["method"] == "exercise_entries.save_template"
    assert params["method"] != "exercise_entries.get_month"
    assert params["days"] == 3
    assert "date" not in params
    assert mock_call.call_args.kwargs.get("method") == "POST"
    assert result is True


def test_exercise_entries_save_template_v1_with_date(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.exercises.entries_save_template_v1(days=7, date=REF_DT)
    params = mock_call.call_args.args[0]
    assert params["date"] == REF_DAYS
    assert params["days"] == 7


def test_exercise_entries_save_template_v1_days_coerced_to_int(fs):
    """`days` is forced through int() in the source."""
    with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
        fs.exercises.entries_save_template_v1(days="5")  # type: ignore[arg-type]
    assert mock_call.call_args.args[0]["days"] == 5


def test_exercise_entries_save_template_v1_date_coercion(fs):
    results = []
    for d in (REF_DT, REF_DATE, REF_TS, float(REF_TS)):
        with patch.object(Fatsecret, "_call", return_value={"success": 1}) as mock_call:
            fs.exercises.entries_save_template_v1(days=1, date=d)
        results.append(mock_call.call_args.args[0])
    for r in results[1:]:
        assert r == results[0]
    assert results[0]["date"] == REF_DAYS


def test_exercise_entries_save_template_v1_mutator_returns_true(fs):
    with patch.object(Fatsecret, "_call", return_value={"success": 1}):
        assert fs.exercises.entries_save_template_v1(days=1) is True
