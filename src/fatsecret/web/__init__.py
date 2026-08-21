"""Unofficial authenticated FatSecret member-website integration."""

from .client import FatsecretWebClient
from .errors import (
    FatsecretWebAuthenticationError,
    FatsecretWebError,
    FatsecretWebParseError,
    FatsecretWebVerificationError,
)
from .models import (
    WebRdiSetting,
    WebRdiUpdate,
    WebRecipeSummary,
    WebRecipeSummaryNutrition,
)

__all__ = [
    "FatsecretWebAuthenticationError",
    "FatsecretWebClient",
    "FatsecretWebError",
    "FatsecretWebParseError",
    "FatsecretWebVerificationError",
    "WebRdiSetting",
    "WebRdiUpdate",
    "WebRecipeSummary",
    "WebRecipeSummaryNutrition",
]
