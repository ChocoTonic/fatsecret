"""Typed Pydantic v2 response models for the FatSecret API.

Generated classes live under ``fatsecret.models._generated``; this module
re-exports the public names for ergonomic ``from fatsecret.models import
Food`` access. Phase 2 adds the recipe / profile / diary models.
"""

from __future__ import annotations

from ._common import FoodType, Ternary, _FS_Base
from ._generated.exercise_diary import \
    Day as ExerciseDay  # alias to avoid Day collision
from ._generated.exercise_diary import (Exercise, ExerciseEntries,
                                        ExerciseEntry, ExerciseTypes)
from ._generated.exercise_diary import Month as ExerciseMonth
from ._generated.food_diary import Day, Month
from ._generated.foods import (Allergen, Allergens, Food, FoodAttributes,
                               FoodEntries, FoodEntry, FoodImage, FoodImages,
                               FoodResults, Foods, FoodsSearch,
                               FoodSubCategories, Preference, Preferences,
                               Serving)
from ._generated.profile_auth import Profile
from ._generated.recipes import (Recipes, RecipesRecipe,
                                 RecipesRecipeRecipeIngredients,
                                 RecipesRecipeRecipeNutrition,
                                 RecipesRecipeRecipeTypes)
from ._generated.weight_diary import \
    Day as WeightDay  # noqa: F401  (re-exported below)
from ._generated.weight_diary import Month as WeightMonth  # noqa: F401

# Friendlier alias: callers expect ``Recipe``, the XSD's anonymous type
# surfaces as ``RecipesRecipe``.
Recipe = RecipesRecipe

__all__ = [
    "Allergen",
    "Allergens",
    "Day",
    "Exercise",
    "ExerciseDay",
    "ExerciseEntries",
    "ExerciseEntry",
    "ExerciseMonth",
    "ExerciseTypes",
    "Food",
    "FoodAttributes",
    "FoodEntries",
    "FoodEntry",
    "FoodImage",
    "FoodImages",
    "FoodResults",
    "FoodSubCategories",
    "FoodType",
    "Foods",
    "FoodsSearch",
    "Month",
    "Preference",
    "Preferences",
    "Profile",
    "Recipe",
    "Recipes",
    "RecipesRecipe",
    "RecipesRecipeRecipeIngredients",
    "RecipesRecipeRecipeNutrition",
    "RecipesRecipeRecipeTypes",
    "Serving",
    "Ternary",
    "WeightDay",
    "WeightMonth",
    "_FS_Base",
]
