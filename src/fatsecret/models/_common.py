"""Cross-cutting types and base class for FatSecret response models.

The generated model modules under ``fatsecret.models._generated`` import
``_FS_Base`` from this module and use the literal aliases (``Ternary``,
``FoodType``) where the XSD declares the corresponding enum simpleType.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class _FS_Base(BaseModel):
    """Base class for every generated FatSecret response model.

    Defaults are deliberately permissive: ``extra="allow"`` so a new
    upstream field doesn't blow up validation, ``populate_by_name=True``
    so callers can use either the field name or its alias, and
    ``str_strip_whitespace=True`` to absorb upstream-side whitespace
    inconsistencies.
    """

    model_config = ConfigDict(
        extra="allow",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def to_dict(self) -> dict:
        """Migration helper: return the v2-style dict shape.

        ``mode="json"`` ensures ``Decimal`` and other non-JSON-native
        types serialize to strings, matching the wire format that v2
        callers were already handling.
        """
        return self.model_dump(mode="json")


# FatSecret's quirky tri-state boolean. Documented only in the XSD.
Ternary = Literal[-1, 0, 1, "Unknown", "True", "False"]


# ``food_type`` enum from the XSD.
FoodType = Literal["Brand", "Generic"]
