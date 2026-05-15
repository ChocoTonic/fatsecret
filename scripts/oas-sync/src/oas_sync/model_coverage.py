"""Single source of truth for typed-response coverage.

Maps ``(tag, unwrap_path_tuple, list_key)`` to ``(model_module, model_class)``.
When an entry exists, the generated resource method wraps the unwrapped raw
payload via ``Model.model_validate(...)`` and the return-type annotation
becomes the model class (or ``list[Model]`` / ``Optional[Model]``).

Operations whose tuple is *not* in the map continue to return raw
``dict`` / ``list[dict]``.

Both ``emit_resource.py`` (codegen of the resource wrappers) and
``assemble.py`` (which stamps an ``x-fatsecret-typed-response`` vendor
extension on every operation) read from this map. Keeping it in one
place ensures the OAS flag and the generated Python stay in lockstep.
"""

from __future__ import annotations


# Resources without XSD coverage (Food Classification, Saved Meals,
# Weight Diary's non-month endpoints, Native APIs, Feedback) have no
# entries here and continue to return raw ``dict`` / ``list[dict]``.
RESPONSE_MODEL_MAP: dict[
    tuple[str, tuple[str, ...], str | None],
    tuple[str, str],
] = {
    # Foods (singular)
    ("Foods", ("food",), None): ("foods", "Food"),
    # Foods (list / search variants)
    ("Foods", ("foods",), "food"): ("foods", "Food"),
    ("Foods", ("foods_search", "results"), "food"): ("foods", "Food"),
    # Profile Foods (same Food model)
    ("Profile Foods", ("foods",), "food"): ("foods", "Food"),
    # Recipes
    ("Recipes", ("recipe",), None): ("recipes", "RecipesRecipe"),
    ("Recipes", ("recipes",), "recipe"): ("recipes", "RecipesRecipe"),
    # Profile Auth
    ("Profile Auth", ("profile",), None): ("profile_auth", "Profile"),
    # Food Diary
    ("Food Diary", ("food_entries",), "food_entry"): ("food_diary", "FoodEntry"),
    ("Food Diary", ("month",), "day"): ("food_diary", "Day"),
    # Exercise Diary
    ("Exercise Diary", ("exercise_entries",), "exercise_entry"): (
        "exercise_diary", "ExerciseEntry",
    ),
    ("Exercise Diary", ("exercise_types",), "exercise"): (
        "exercise_diary", "Exercise",
    ),
    ("Exercise Diary", ("month",), "day"): ("exercise_diary", "Day"),
    # Weight Diary (only get_month is XSD-covered)
    ("Weight Diary", ("month",), "day"): ("weight_diary", "Day"),
}


__all__ = ["RESPONSE_MODEL_MAP"]
