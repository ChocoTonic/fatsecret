"""Recipes resource — recipe.get, recipes.search, recipe_types.get, recipe favorites."""

from __future__ import annotations

from typing import Any, Optional, Union

from ._base import BaseResource


class RecipesResource(BaseResource):
    """Resource methods for the OAS `Recipes` tag."""

    # ------------------------- Recipes: recipe.get -------------------------

    def get_v1(self, recipe_id: str, region: Optional[str] = None) -> dict:
        """recipe.get v1 (DEPRECATED upstream)."""
        params = {"method": "recipe.get", "recipe_id": recipe_id}
        self._client._set_optional(params, [("region", region)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipe")

    def get_v2(self, recipe_id: str, region: Optional[str] = None) -> dict:
        """recipe.get v2 (current). Adds grams_per_portion."""
        params = {"method": "recipe.get.v2", "recipe_id": recipe_id}
        self._client._set_optional(params, [("region", region)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipe")

    # ------------------------- Recipes: recipes.search -------------------------

    def search_v1(
        self,
        search_expression: Optional[str] = None,
        recipe_type: Optional[str] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> list:
        """recipes.search v1 (DEPRECATED upstream)."""
        params: dict = {"method": "recipes.search"}
        self._client._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("recipe_type", recipe_type),
                ("page_number", page_number),
                ("max_results", max_results),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipes", list_key="recipe")

    def search_v2(
        self,
        search_expression: Optional[str] = None,
        must_have_images: Optional[bool] = None,
        calories_from: Optional[int] = None,
        calories_to: Optional[int] = None,
        carb_percentage_from: Optional[int] = None,
        carb_percentage_to: Optional[int] = None,
        protein_percentage_from: Optional[int] = None,
        protein_percentage_to: Optional[int] = None,
        fat_percentage_from: Optional[int] = None,
        fat_percentage_to: Optional[int] = None,
        prep_time_from: Optional[int] = None,
        prep_time_to: Optional[int] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        sort_by: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list:
        """recipes.search v2 (DEPRECATED upstream). Adds nutritional/time filters."""
        params: dict = {"method": "recipes.search.v2"}
        self._client._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("must_have_images", must_have_images),
                ("calories.from", calories_from),
                ("calories.to", calories_to),
                ("carb_percentage.from", carb_percentage_from),
                ("carb_percentage.to", carb_percentage_to),
                ("protein_percentage.from", protein_percentage_from),
                ("protein_percentage.to", protein_percentage_to),
                ("fat_percentage.from", fat_percentage_from),
                ("fat_percentage.to", fat_percentage_to),
                ("prep_time.from", prep_time_from),
                ("prep_time.to", prep_time_to),
                ("page_number", page_number),
                ("max_results", max_results),
                ("sort_by", sort_by),
                ("region", region),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipes", list_key="recipe")

    def search_v3(
        self,
        search_expression: Optional[str] = None,
        recipe_types: Optional[str] = None,
        recipe_types_matchall: Optional[bool] = None,
        must_have_images: Optional[bool] = None,
        calories_from: Optional[int] = None,
        calories_to: Optional[int] = None,
        carb_percentage_from: Optional[int] = None,
        carb_percentage_to: Optional[int] = None,
        protein_percentage_from: Optional[int] = None,
        protein_percentage_to: Optional[int] = None,
        fat_percentage_from: Optional[int] = None,
        fat_percentage_to: Optional[int] = None,
        prep_time_from: Optional[int] = None,
        prep_time_to: Optional[int] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        sort_by: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list:
        """recipes.search v3 (current). Adds recipe_types comma-list + matchall."""
        params: dict = {"method": "recipes.search.v3"}
        self._client._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("recipe_types", recipe_types),
                ("recipe_types_matchall", recipe_types_matchall),
                ("must_have_images", must_have_images),
                ("calories.from", calories_from),
                ("calories.to", calories_to),
                ("carb_percentage.from", carb_percentage_from),
                ("carb_percentage.to", carb_percentage_to),
                ("protein_percentage.from", protein_percentage_from),
                ("protein_percentage.to", protein_percentage_to),
                ("fat_percentage.from", fat_percentage_from),
                ("fat_percentage.to", fat_percentage_to),
                ("prep_time.from", prep_time_from),
                ("prep_time.to", prep_time_to),
                ("page_number", page_number),
                ("max_results", max_results),
                ("sort_by", sort_by),
                ("region", region),
            ],
        )
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipes", list_key="recipe")

    # ------------------------- Recipes: recipe_types.get -------------------------

    def types_get_v1(self) -> list:
        """recipe_types.get v1 (DEPRECATED upstream)."""
        payload = self._client._call({"method": "recipe_types.get"})
        return self._client._unwrap(payload, "recipe_types", list_key="recipe_type")

    def types_get_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """recipe_types.get v2 (current). Region/language are Premier-exclusive."""
        params = {"method": "recipe_types.get.v2"}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "recipe_types", list_key="recipe_type")

    # ------------------------- Recipes: favorites -------------------------

    def add_favorite_v1(self, recipe_id: str) -> Union[bool, Any]:
        """recipe.add_favorite v1. Fixes the legacy plural-typo bug (uses singular `recipe.add_favorite`)."""
        payload = self._client._call(
            {"method": "recipe.add_favorite", "recipe_id": recipe_id}, method="POST"
        )
        return self._client._mutator_success(payload)

    def delete_favorite_v1(self, recipe_id: str) -> Union[bool, Any]:
        """recipe.delete_favorite v1. Fixes the legacy plural-typo bug."""
        payload = self._client._call(
            {"method": "recipe.delete_favorite", "recipe_id": recipe_id},
            method="DELETE",
        )
        return self._client._mutator_success(payload)

    def get_favorites_v1(self) -> list:
        """recipes.get_favorites v1 (DEPRECATED upstream). api_method_param: recipe.get_favorites."""
        payload = self._client._call({"method": "recipe.get_favorites"})
        return self._client._unwrap(payload, "recipes", list_key="recipe")

    def get_favorites_v2(self) -> list:
        """recipes.get_favorites v2 (current). api_method_param: recipe.get_favorites.v2."""
        payload = self._client._call({"method": "recipe.get_favorites.v2"})
        return self._client._unwrap(payload, "recipes", list_key="recipe")
