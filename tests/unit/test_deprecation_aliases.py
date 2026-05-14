"""Verify every unsuffixed legacy method emits a DeprecationWarning that
references its v1 replacement (and the latest _vN where the message mentions it).

All HTTP is suppressed by patching Fatsecret._call to return a benign dict.
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret


# (method_name, args, kwargs, expected_v1_target, optional_latest_vN_hint)
#
# expected_v1_target is the v1 name explicitly referenced in the warning text.
# When the warning also mentions a "latest" upstream version, list it; some
# aliases have no latest hint (single-version method families).
ALIASES = [
    ("exercises_get", (), {}, "exercises_get_v1", "exercises_get_v2"),
    (
        "exercise_entries_commit_day",
        (),
        {},
        "exercise_entries_commit_day_v1",
        None,
    ),
    (
        "exercise_entries_get",
        (),
        {},
        "exercise_entries_get_v1",
        "exercise_entries_get_v2",
    ),
    (
        "exercise_entries_get_month",
        (),
        {},
        "exercise_entries_get_month_v1",
        "exercise_entries_get_month_v2",
    ),
    (
        "exercise_entries_save_template",
        (5,),
        {},
        "exercise_entries_save_template_v1",
        None,
    ),
    (
        "exercise_entry_edit",
        ("to_id", "from_id", 10),
        {},
        "exercise_entry_edit_v1",
        None,
    ),
    ("food_add_favorite", ("123",), {}, "food_add_favorite_v1", None),
    ("food_delete_favorite", ("123",), {}, "food_delete_favorite_v1", None),
    ("food_get", ("123",), {}, "food_get_v1", "food_get_v5"),
    (
        "food_find_id_for_barcode",
        ("0000000000000",),
        {},
        "food_find_id_for_barcode_v1",
        "food_find_id_for_barcode_v2",
    ),
    (
        "foods_get_favorites",
        (),
        {},
        "foods_get_favorites_v1",
        "foods_get_favorites_v2",
    ),
    (
        "foods_get_most_eaten",
        (),
        {"meal": "lunch"},
        "foods_get_most_eaten_v1",
        "foods_get_most_eaten_v2",
    ),
    (
        "foods_get_recently_eaten",
        (),
        {"meal": "dinner"},
        "foods_get_recently_eaten_v1",
        "foods_get_recently_eaten_v2",
    ),
    ("foods_search", ("apple",), {}, "foods_search_v1", "foods_search_v5"),
    (
        "foods_autocomplete",
        ("chic",),
        {},
        "foods_autocomplete_v1",
        "foods_autocomplete_v2",
    ),
    ("food_entries_copy", (1, 2), {}, "food_entries_copy_v1", None),
    (
        "food_entries_copy_saved_meal",
        ("mid", "breakfast"),
        {},
        "food_entries_copy_saved_meal_v1",
        None,
    ),
    (
        "food_entries_get",
        (),
        {"food_entry_id": "fe1"},
        "food_entries_get_v1",
        "food_entries_get_v2",
    ),
    (
        "food_entries_get_month",
        (),
        {},
        "food_entries_get_month_v1",
        "food_entries_get_month_v2",
    ),
    (
        "food_entry_create",
        ("fid", "name", "sid", 1.0, "lunch"),
        {},
        "food_entry_create_v1",
        None,
    ),
    ("food_entry_delete", ("fe1",), {}, "food_entry_delete_v1", None),
    ("food_entry_edit", ("fe1",), {}, "food_entry_edit_v1", None),
    ("saved_meal_create", ("m_name",), {}, "saved_meal_create_v1", None),
    ("saved_meal_delete", ("mid",), {}, "saved_meal_delete_v1", None),
    ("saved_meal_edit", ("mid",), {}, "saved_meal_edit_v1", None),
    # plural rename — message references "saved_meals_get_v1" and v2
    (
        "saved_meal_get",
        (),
        {},
        "saved_meals_get_v1",
        "saved_meals_get_v2",
    ),
    (
        "saved_meal_item_add",
        ("mid", "fid", "name", "sid", 1.0),
        {},
        "saved_meal_item_add_v1",
        None,
    ),
    ("saved_meal_item_delete", ("mi1",), {}, "saved_meal_item_delete_v1", None),
    ("saved_meal_item_edit", ("mi1",), {}, "saved_meal_item_edit_v1", None),
    (
        "saved_meal_items_get",
        ("mid",),
        {},
        "saved_meal_items_get_v1",
        "saved_meal_items_get_v2",
    ),
    ("profile_create", (), {}, "profile_create_v1", None),
    ("profile_get", (), {}, "profile_get_v1", None),
    ("profile_get_auth", ("user-123",), {}, "profile_get_auth_v1", None),
    # plural typo fix — message references singular recipe_add_favorite_v1
    (
        "recipes_add_favorite",
        ("rid",),
        {},
        "recipe_add_favorite_v1",
        None,
    ),
    (
        "recipes_delete_favorite",
        ("rid",),
        {},
        "recipe_delete_favorite_v1",
        None,
    ),
    ("recipe_get", ("rid",), {}, "recipe_get_v1", "recipe_get_v2"),
    (
        "recipes_get_favorites",
        (),
        {},
        "recipes_get_favorites_v1",
        "recipes_get_favorites_v2",
    ),
    (
        "recipes_search",
        ("query",),
        {},
        "recipes_search_v1",
        "recipes_search_v3",
    ),
    (
        "recipe_types_get",
        (),
        {},
        "recipe_types_get_v1",
        "recipe_types_get_v2",
    ),
    ("weight_update", (70.5,), {}, "weight_update_v1", None),
    (
        "weights_get_month",
        (),
        {},
        "weights_get_month_v1",
        "weights_get_month_v2",
    ),
]


@pytest.fixture
def fs():
    """Fatsecret instance without making real HTTP calls."""
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        instance = Fatsecret("ck", "cs")
    return instance


def test_alias_coverage_complete():
    """Sanity: alias table covers all 41 legacy methods."""
    assert len(ALIASES) == 41
    assert len({a[0] for a in ALIASES}) == 41


@pytest.mark.parametrize(
    "method_name,args,kwargs,v1_target,latest_hint",
    ALIASES,
    ids=[a[0] for a in ALIASES],
)
def test_legacy_alias_emits_deprecation_warning(
    fs, method_name, args, kwargs, v1_target, latest_hint
):
    # Patch _call to a no-op success payload so the underlying v1 method
    # produces a value without any network activity.
    with patch.object(Fatsecret, "_call", return_value={"success": 1}):
        method = getattr(fs, method_name)
        with pytest.warns(DeprecationWarning) as record:
            method(*args, **kwargs)

    # Find the DeprecationWarning that targets our legacy alias (filters out
    # any unrelated warnings emitted by transitive code).
    matching = [
        w
        for w in record
        if issubclass(w.category, DeprecationWarning)
        and f"Fatsecret.{method_name}()" in str(w.message)
    ]
    assert matching, f"No DeprecationWarning for {method_name}"
    msg = str(matching[0].message)

    # Message must mention the v1 replacement target
    assert v1_target in msg, f"{method_name}: missing v1 target {v1_target!r} in {msg!r}"
    if latest_hint:
        assert (
            latest_hint in msg
        ), f"{method_name}: missing latest hint {latest_hint!r} in {msg!r}"
