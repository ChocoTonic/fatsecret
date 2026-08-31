"""Typed models for the unofficial authenticated FatSecret member website."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from ..models._common import _FS_Base


class WebMealType(str, Enum):
    """Recipe meal types supported by the member edit form."""

    APPETIZERS = "appetizers"
    SOUPS = "soups"
    MAIN_DISHES = "main_dishes"
    SIDE_DISHES = "side_dishes"
    BREADS_AND_BAKED_PRODUCTS = "breads_and_baked_products"
    SALADS_AND_SALAD_DRESSINGS = "salads_and_salad_dressings"
    SAUCES_AND_CONDIMENTS = "sauces_and_condiments"
    DESSERTS = "desserts"
    SNACKS = "snacks"
    BEVERAGES = "beverages"
    OTHER = "other"
    BREAKFAST = "breakfast"
    LUNCH = "lunch"


class WebNutrition(_FS_Base):
    """Nutrition values parsed from a recipe or ingredient row."""

    calories: Optional[Decimal] = Field(default=None, ge=0)
    fat_g: Optional[Decimal] = Field(default=None, ge=0)
    saturated_fat_g: Optional[Decimal] = Field(default=None, ge=0)
    unsaturated_fat_g: Optional[Decimal] = Field(default=None, ge=0)
    carbohydrate_g: Optional[Decimal] = Field(default=None, ge=0)
    fiber_g: Optional[Decimal] = Field(default=None, ge=0)
    sugar_g: Optional[Decimal] = Field(default=None, ge=0)
    protein_g: Optional[Decimal] = Field(default=None, ge=0)
    cholesterol_mg: Optional[Decimal] = Field(default=None, ge=0)
    sodium_mg: Optional[Decimal] = Field(default=None, ge=0)


class WebRecipeSummaryNutrition(WebNutrition):
    """Backward-compatible name for cookbook summary nutrition."""


class WebRecipeSummary(_FS_Base):
    """Recipe metadata available from one member-cookbook listing row."""

    recipe_id: int = Field(gt=0)
    title: str = Field(min_length=1)
    description: str
    status: str = Field(min_length=1)
    nutrition: WebRecipeSummaryNutrition
    preview_url: str
    edit_url: str


class WebFoodPortion(_FS_Base):
    """One serving option offered for a food in a destination recipe."""

    portion_id: int
    label: str = Field(min_length=1)
    is_grams: bool

    @field_validator("portion_id")
    @classmethod
    def _nonzero_portion_id(cls, value: int) -> int:
        if value == 0:
            raise ValueError("portion_id must not be zero")
        return value


class WebFoodPortions(_FS_Base):
    """Portion choices resolved directly from a known FatSecret food ID."""

    food_id: int = Field(gt=0)
    food_name: str = Field(min_length=1)
    portions: list[WebFoodPortion] = Field(min_length=1)


class _WebWriteModel(_FS_Base):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class WebIngredientWrite(_WebWriteModel):
    """Ingredient input using a known food ID and an exact or grams portion."""

    food_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    portion_id: Optional[int] = None
    unit: Optional[Literal["grams"]] = None

    @model_validator(mode="after")
    def _portion_or_grams(self) -> "WebIngredientWrite":
        if self.portion_id == 0:
            raise ValueError("portion_id must not be zero")
        if self.portion_id is not None and self.unit is not None:
            raise ValueError("unit must be omitted when portion_id is provided")
        if self.portion_id is None:
            self.unit = "grams"
        return self


class WebRecipeIngredient(_FS_Base):
    """Fully hydrated member-recipe ingredient."""

    entry_id: int = Field(gt=0)
    food_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    portion_id: int
    portion_name: str = Field(min_length=1)
    display_text: str = Field(min_length=1)
    nutrition_total: WebNutrition

    @field_validator("portion_id")
    @classmethod
    def _nonzero_portion_id(cls, value: int) -> int:
        if value == 0:
            raise ValueError("portion_id must not be zero")
        return value

    def as_write(self) -> WebIngredientWrite:
        """Return an exact write representation suitable for copying."""

        return WebIngredientWrite(
            food_id=self.food_id,
            amount=self.amount,
            portion_id=self.portion_id,
        )


class WebRecipeWrite(_WebWriteModel):
    """Writable recipe metadata; ingredients are managed as child resources."""

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    servings: Decimal = Field(gt=0)
    prep_minutes: int = Field(ge=0)
    cook_minutes: int = Field(ge=0)
    meal_types: list[WebMealType] = Field(default_factory=list)
    directions: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("meal_types")
    @classmethod
    def _unique_meal_types(cls, values: list[WebMealType]) -> list[WebMealType]:
        if len(values) != len(set(values)):
            raise ValueError("meal_types must not contain duplicates")
        return values

    @field_validator("directions")
    @classmethod
    def _non_empty_directions(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("directions must not contain empty steps")
        return values


class WebRecipeDetail(_FS_Base):
    """Writable metadata and fully hydrated ingredients for an owned recipe."""

    recipe_id: int = Field(gt=0)
    title: str = Field(min_length=1)
    description: str
    status: str = Field(min_length=1)
    nutrition_per_serving: WebNutrition
    preview_url: str
    edit_url: str
    author: Optional[str] = None
    date_published: Optional[date] = None
    servings: Decimal = Field(gt=0)
    prep_minutes: int = Field(ge=0)
    cook_minutes: int = Field(ge=0)
    meal_types: list[WebMealType]
    directions: list[str]
    sharing: bool
    images: list[str] = Field(default_factory=list)
    ingredients: list[WebRecipeIngredient]

    def as_write(self, *, title: Optional[str] = None) -> WebRecipeWrite:
        """Return metadata suitable for replacement or a new copy."""

        return WebRecipeWrite(
            title=title or self.title,
            description=self.description,
            servings=self.servings,
            prep_minutes=self.prep_minutes,
            cook_minutes=self.cook_minutes,
            meal_types=self.meal_types,
            directions=self.directions,
        )


class WebRecipeDeleteResult(_FS_Base):
    """Verified idempotent recipe deletion result."""

    recipe_id: int = Field(gt=0)
    deleted: bool


class WebRecipeCopyRequest(_WebWriteModel):
    """Requested title for a copy of an existing member recipe."""

    title: str = Field(min_length=1, max_length=255)


class WebRecipeCopyOperation(_FS_Base):
    """Durable status for a multi-request recipe copy."""

    operation_id: str = Field(min_length=1)
    status: Literal["pending", "running", "waiting", "completed", "failed", "unknown"]
    source_recipe_id: int = Field(gt=0)
    target_title: str = Field(min_length=1)
    target_recipe_id: Optional[int] = Field(default=None, gt=0)
    completed_ingredient_count: int = Field(default=0, ge=0)
    total_ingredient_count: Optional[int] = Field(default=None, ge=0)
    retry_after: Optional[datetime] = None
    result: Optional[WebRecipeDetail] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _completed_has_result(self) -> "WebRecipeCopyOperation":
        if self.status == "completed" and self.result is None:
            raise ValueError("completed copy operation must contain a result")
        return self


class WebRdiSetting(_FS_Base):
    """The RDI currently saved to the member account."""

    calories_per_day: int = Field(gt=0)
    effective_date: date


class WebRdiUpdate(_FS_Base):
    """Verified result of replacing the member account's RDI."""

    requested_calories_per_day: int = Field(gt=0)
    previous: WebRdiSetting
    current: WebRdiSetting


__all__ = [
    "WebFoodPortion",
    "WebFoodPortions",
    "WebIngredientWrite",
    "WebMealType",
    "WebNutrition",
    "WebRdiSetting",
    "WebRdiUpdate",
    "WebRecipeCopyOperation",
    "WebRecipeCopyRequest",
    "WebRecipeDeleteResult",
    "WebRecipeDetail",
    "WebRecipeIngredient",
    "WebRecipeSummary",
    "WebRecipeSummaryNutrition",
    "WebRecipeWrite",
]
