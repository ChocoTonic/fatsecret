"""Resource wrapper for the OAS `Food Classification` tag."""

from __future__ import annotations

from typing import Optional

from ._base import BaseResource


class ClassificationResource(BaseResource):
    """Resource methods for the OAS `Food Classification` tag."""

    def brands_get_v1(
        self,
        starts_with: str,
        brand_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_brands.get v1 (DEPRECATED upstream). Premier."""
        params = {"method": "food_brands.get", "starts_with": starts_with}
        self._client._set_optional(
            params,
            [("brand_type", brand_type), ("region", region), ("language", language)],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_brands", list_key="food_brand")

    def brands_get_v2(
        self,
        starts_with: str,
        brand_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_brands.get v2 (current). Premier."""
        params = {"method": "food_brands.get.v2", "starts_with": starts_with}
        self._client._set_optional(
            params,
            [("brand_type", brand_type), ("region", region), ("language", language)],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_brands", list_key="food_brand")

    def categories_get_v1(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """food_categories.get v1 (DEPRECATED upstream). Premier."""
        params = {"method": "food_categories.get"}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_categories", list_key="food_category")

    def categories_get_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """food_categories.get v2 (current). Premier."""
        params = {"method": "food_categories.get.v2"}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_categories", list_key="food_category")

    def sub_categories_get_v1(
        self,
        food_category_id: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_sub_categories.get v1 (DEPRECATED upstream). Premier."""
        params = {
            "method": "food_sub_categories.get",
            "food_category_id": food_category_id,
        }
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(
            payload, "food_sub_categories", list_key="food_sub_category"
        )

    def sub_categories_get_v2(
        self,
        food_category_id: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_sub_categories.get v2 (current). Premier."""
        params = {
            "method": "food_sub_categories.get.v2",
            "food_category_id": food_category_id,
        }
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(
            payload, "food_sub_categories", list_key="food_sub_category"
        )
