"""Phase 1 v2.0 resource-surface parity tests.

Every namespaced call (e.g. ``fs.foods.search_v5(...)``) must delegate
to its flat-method equivalent (``fs.foods_search_v5(...)``) with the
exact same args/kwargs and return value. This is exhaustive — one
parametrize case per delegation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fatsecret import Fatsecret

# (resource_attr, namespaced_method, flat_method_on_client)
DELEGATIONS: list[tuple[str, str, str]] = [
    # Foods (14)
    ("foods", "autocomplete_v1", "foods_autocomplete_v1"),
    ("foods", "autocomplete_v2", "foods_autocomplete_v2"),
    ("foods", "find_id_for_barcode_v1", "food_find_id_for_barcode_v1"),
    ("foods", "find_id_for_barcode_v2", "food_find_id_for_barcode_v2"),
    ("foods", "get_v1", "food_get_v1"),
    ("foods", "get_v2", "food_get_v2"),
    ("foods", "get_v3", "food_get_v3"),
    ("foods", "get_v4", "food_get_v4"),
    ("foods", "get_v5", "food_get_v5"),
    ("foods", "search_v1", "foods_search_v1"),
    ("foods", "search_v2", "foods_search_v2"),
    ("foods", "search_v3", "foods_search_v3"),
    ("foods", "search_v4", "foods_search_v4"),
    ("foods", "search_v5", "foods_search_v5"),
    # Classification (6)
    ("classification", "brands_get_v1", "food_brands_get_v1"),
    ("classification", "brands_get_v2", "food_brands_get_v2"),
    ("classification", "categories_get_v1", "food_categories_get_v1"),
    ("classification", "categories_get_v2", "food_categories_get_v2"),
    ("classification", "sub_categories_get_v1", "food_sub_categories_get_v1"),
    ("classification", "sub_categories_get_v2", "food_sub_categories_get_v2"),
    # Recipes (11)
    ("recipes", "add_favorite_v1", "recipe_add_favorite_v1"),
    ("recipes", "delete_favorite_v1", "recipe_delete_favorite_v1"),
    ("recipes", "get_favorites_v1", "recipes_get_favorites_v1"),
    ("recipes", "get_favorites_v2", "recipes_get_favorites_v2"),
    ("recipes", "get_v1", "recipe_get_v1"),
    ("recipes", "get_v2", "recipe_get_v2"),
    ("recipes", "search_v1", "recipes_search_v1"),
    ("recipes", "search_v2", "recipes_search_v2"),
    ("recipes", "search_v3", "recipes_search_v3"),
    ("recipes", "types_get_v1", "recipe_types_get_v1"),
    ("recipes", "types_get_v2", "recipe_types_get_v2"),
    # Profile Foods (10)
    ("profile_foods", "add_favorite_v1", "food_add_favorite_v1"),
    ("profile_foods", "create_v1", "food_create_v1"),
    ("profile_foods", "create_v2", "food_create_v2"),
    ("profile_foods", "delete_favorite_v1", "food_delete_favorite_v1"),
    ("profile_foods", "get_favorites_v1", "foods_get_favorites_v1"),
    ("profile_foods", "get_favorites_v2", "foods_get_favorites_v2"),
    ("profile_foods", "get_most_eaten_v1", "foods_get_most_eaten_v1"),
    ("profile_foods", "get_most_eaten_v2", "foods_get_most_eaten_v2"),
    ("profile_foods", "get_recently_eaten_v1", "foods_get_recently_eaten_v1"),
    ("profile_foods", "get_recently_eaten_v2", "foods_get_recently_eaten_v2"),
    # Meals (10)
    ("meals", "create_v1", "saved_meal_create_v1"),
    ("meals", "delete_v1", "saved_meal_delete_v1"),
    ("meals", "edit_v1", "saved_meal_edit_v1"),
    ("meals", "get_v1", "saved_meals_get_v1"),
    ("meals", "get_v2", "saved_meals_get_v2"),
    ("meals", "item_add_v1", "saved_meal_item_add_v1"),
    ("meals", "item_delete_v1", "saved_meal_item_delete_v1"),
    ("meals", "item_edit_v1", "saved_meal_item_edit_v1"),
    ("meals", "items_get_v1", "saved_meal_items_get_v1"),
    ("meals", "items_get_v2", "saved_meal_items_get_v2"),
    # Diary (9)
    ("diary", "entries_copy_saved_meal_v1", "food_entries_copy_saved_meal_v1"),
    ("diary", "entries_copy_v1", "food_entries_copy_v1"),
    ("diary", "entries_get_month_v1", "food_entries_get_month_v1"),
    ("diary", "entries_get_month_v2", "food_entries_get_month_v2"),
    ("diary", "entries_get_v1", "food_entries_get_v1"),
    ("diary", "entries_get_v2", "food_entries_get_v2"),
    ("diary", "entry_create_v1", "food_entry_create_v1"),
    ("diary", "entry_delete_v1", "food_entry_delete_v1"),
    ("diary", "entry_edit_v1", "food_entry_edit_v1"),
    # Exercises (9)
    ("exercises", "entries_commit_day_v1", "exercise_entries_commit_day_v1"),
    ("exercises", "entries_get_month_v1", "exercise_entries_get_month_v1"),
    ("exercises", "entries_get_month_v2", "exercise_entries_get_month_v2"),
    ("exercises", "entries_get_v1", "exercise_entries_get_v1"),
    ("exercises", "entries_get_v2", "exercise_entries_get_v2"),
    ("exercises", "entries_save_template_v1", "exercise_entries_save_template_v1"),
    ("exercises", "entry_edit_v1", "exercise_entry_edit_v1"),
    ("exercises", "list_v1", "exercises_get_v1"),
    ("exercises", "list_v2", "exercises_get_v2"),
    # Weight (3)
    ("weight", "get_month_v1", "weights_get_month_v1"),
    ("weight", "get_month_v2", "weights_get_month_v2"),
    ("weight", "update_v1", "weight_update_v1"),
    # Profile (3)
    ("profile", "create_v1", "profile_create_v1"),
    ("profile", "get_auth_v1", "profile_get_auth_v1"),
    ("profile", "get_v1", "profile_get_v1"),
    # Native (3)
    ("native", "image_recognition_v1", "image_recognition_v1"),
    ("native", "image_recognition_v2", "image_recognition_v2"),
    ("native", "natural_language_processing_v1", "natural_language_processing_v1"),
    # Feedback (1)
    ("feedback", "submit_v1", "feedback_v1"),
]


@pytest.fixture
def client() -> Fatsecret:
    return Fatsecret("dummy_key", "dummy_secret")


def test_all_resources_attached(client: Fatsecret) -> None:
    """Every OAS-tag resource is reachable from the client."""
    expected = {
        "foods", "classification", "recipes", "profile_foods", "meals",
        "diary", "exercises", "weight", "profile", "native", "feedback",
    }
    for attr in expected:
        assert hasattr(client, attr), f"missing resource attribute: {attr}"


def test_delegation_table_covers_every_resource_method(client: Fatsecret) -> None:
    """The parametrized table below must cover EVERY public method on EVERY
    resource. If a new method is added without a parity entry, this fails."""
    actual = set()
    for resource_attr in {d[0] for d in DELEGATIONS}:
        resource = getattr(client, resource_attr)
        for name in dir(resource):
            if name.startswith("_"):
                continue
            actual.add((resource_attr, name))
    declared = {(d[0], d[1]) for d in DELEGATIONS}
    missing_in_table = actual - declared
    extra_in_table = declared - actual
    assert not missing_in_table, f"resource methods not in delegation table: {missing_in_table}"
    assert not extra_in_table, f"delegation table references missing methods: {extra_in_table}"


@pytest.mark.parametrize(
    "resource_attr,ns_method,flat_method",
    DELEGATIONS,
    ids=[f"{d[0]}.{d[1]}->{d[2]}" for d in DELEGATIONS],
)
def test_namespaced_method_delegates_to_flat(
    client: Fatsecret,
    resource_attr: str,
    ns_method: str,
    flat_method: str,
) -> None:
    """Each namespaced call forwards args/kwargs verbatim to the flat method
    and returns the flat method's return value."""
    resource = getattr(client, resource_attr)
    with patch.object(client, flat_method) as mock_flat:
        mock_flat.return_value = "sentinel"
        result = getattr(resource, ns_method)("pos1", "pos2", kw="value")
    mock_flat.assert_called_once_with("pos1", "pos2", kw="value")
    assert result == "sentinel"


def test_delegation_count_matches_expected_total() -> None:
    """Locks in the surface size for v2.0 Phase 1: 79 namespaced methods."""
    assert len(DELEGATIONS) == 79
