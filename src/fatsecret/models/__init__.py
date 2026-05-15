"""Typed Pydantic v2 response models for the FatSecret API.

Generated classes live under ``fatsecret.models._generated``; this module
re-exports the public names for ergonomic ``from fatsecret.models import
Food`` access.
"""

from __future__ import annotations

from ._common import _FS_Base, FoodType, Ternary
from ._generated.foods import (
    Allergen,
    Allergens,
    Food,
    FoodAttributes,
    FoodEntries,
    FoodEntry,
    FoodImage,
    FoodImages,
    FoodResults,
    Foods,
    FoodsSearch,
    FoodSubCategories,
    Preference,
    Preferences,
    Serving,
)

__all__ = [
    "Allergen",
    "Allergens",
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
    "Preference",
    "Preferences",
    "Serving",
    "Ternary",
    "_FS_Base",
]
