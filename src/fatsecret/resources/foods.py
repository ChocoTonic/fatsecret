"""Resource wrapper for the OAS ``Foods`` tag."""

from __future__ import annotations

from typing import Any, Optional

from ._base import BaseResource


class FoodsResource(BaseResource):
    """Resource methods for the OAS `Foods` tag.

    Phase 1: pure-delegation over the flat ``foods_*`` / ``food_*``
    methods on :class:`Fatsecret`. Future phases swap delegation for
    OAS-codegen'd implementations.
    """

    def autocomplete_v1(
        self,
        expression: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
    ) -> list:
        """foods.autocomplete v1 (DEPRECATED upstream). Premier-only."""
        params = {"method": "foods.autocomplete", "expression": expression}
        self._client._set_optional(params, [("max_results", max_results), ("region", region)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "suggestions", list_key="suggestion")

    def autocomplete_v2(
        self,
        expression: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
    ) -> list:
        """foods.autocomplete v2 (current). Premier-only."""
        params = {"method": "foods.autocomplete.v2", "expression": expression}
        self._client._set_optional(params, [("max_results", max_results), ("region", region)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "suggestions", list_key="suggestion")

    def find_id_for_barcode_v1(
        self,
        barcode: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.find_id_for_barcode v1. Premier (`barcode` scope). Returns food_id (0 if no match)."""
        params = {"method": "food.find_id_for_barcode", "barcode": barcode}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_id")

    def find_id_for_barcode_v2(
        self,
        barcode: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.find_id_for_barcode v2. Returns full food record. Premier (`barcode` scope)."""
        params = {"method": "food.find_id_for_barcode.v2", "barcode": barcode}
        self._client._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food")

    def get_v1(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v1 (DEPRECATED upstream). Vitamins A/C, calcium, iron reported as %DV."""
        params = {"method": "food.get", "food_id": food_id}
        self._client._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food")

    def get_v2(self, food_id, region=None, language=None):
        """Returns detailed nutritional information for the specified food.
        Use this call to display nutrition values for a food to users.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """
        params = {"method": "food.get.v2", "food_id": food_id, "format": "json"}
        if region:
            params["region"] = region
        if language:
            params["language"] = language
        response = self._client.session.get(self._client.api_url, params=params)
        return self._client.valid_response(response)

    def get_v3(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v3 (DEPRECATED upstream). Schema near-identical to v2."""
        params = {"method": "food.get.v3", "food_id": food_id}
        self._client._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food")

    def get_v4(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v4 (DEPRECATED upstream). Adds food_images and food_attributes (allergens, preferences)."""
        params = {"method": "food.get.v4", "food_id": food_id}
        self._client._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food")

    def get_v5(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v5 (current). Brand foods get derived 100g/100ml servings with serving_id=0."""
        params = {"method": "food.get.v5", "food_id": food_id}
        self._client._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food")

    def search_v1(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        generic_description: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v1. Lightweight result set (no nested servings).

        Region/language are Premier-exclusive on v1.
        """
        params = {"method": "foods.search", "search_expression": search_expression}
        self._client._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("generic_description", generic_description),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods", list_key="food")

    def search_v2(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v2 (DEPRECATED upstream). Returns nested servings + nutrition. Premier."""
        params = {"method": "foods.search.v2", "search_expression": search_expression}
        self._client._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods_search", "results", list_key="food")

    def search_v3(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v3 (DEPRECATED upstream). Adds include_food_images and include_food_attributes. Premier."""
        params = {"method": "foods.search.v3", "search_expression": search_expression}
        self._client._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods_search", "results", list_key="food")

    def search_v4(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v4 (DEPRECATED upstream). Brand foods include derived 100g/100ml servings. Premier."""
        params = {"method": "foods.search.v4", "search_expression": search_expression}
        self._client._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods_search", "results", list_key="food")

    def search_v5(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        food_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v5 (current). Adds `food_type` filter ('none'/'generic'/'brand'). Premier."""
        params = {"method": "foods.search.v5", "search_expression": search_expression}
        self._client._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("food_type", food_type),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods_search", "results", list_key="food")
