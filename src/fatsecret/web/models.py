"""Typed models for the unofficial authenticated FatSecret member website."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import Field

from ..models._common import _FS_Base


class WebRecipeSummaryNutrition(_FS_Base):
    """Per-serving nutrition displayed for a recipe in the member cookbook."""

    calories: Optional[Decimal] = Field(default=None)
    fat_g: Optional[Decimal] = Field(default=None)
    carbohydrate_g: Optional[Decimal] = Field(default=None)
    protein_g: Optional[Decimal] = Field(default=None)


class WebRecipeSummary(_FS_Base):
    """Recipe metadata available from one member-cookbook listing row."""

    recipe_id: int
    title: str
    description: str
    status: str
    nutrition: WebRecipeSummaryNutrition
    preview_url: str
    edit_url: str


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
    "WebRdiSetting",
    "WebRdiUpdate",
    "WebRecipeSummary",
    "WebRecipeSummaryNutrition",
]
