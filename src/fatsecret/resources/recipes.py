"""Recipes resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

from typing import Optional

from ..models._generated.recipes import RecipesRecipe
from ._generated.recipes import RecipesResource as _GeneratedRecipesResource


class RecipesResource(_GeneratedRecipesResource):
    """Generated Recipes resource plus dotted-key and legacy-typo overrides.

    Hand overrides:

      * ``search_v2`` / ``search_v3`` — the upstream API expects dotted
        parameter names (``calories.from``, ``carb_percentage.to``, etc.) but
        Python identifiers cannot contain ``.``.  Codegen has no way to know
        about that translation, so we re-emit these two methods with the
        explicit snake -> dotted mapping.
      * ``get_favorites_v1`` / ``get_favorites_v2`` / ``add_favorite_v1`` /
        ``delete_favorite_v1`` — the docs list these under ``recipes.*``
        (plural) but the actual API expects ``recipe.*`` (singular).
        Generation is driven from the docs, so we patch the ``method=`` value.
    """

    def add_favorite_v1(self, recipe_id: str):
        payload = self._client._call(
            {"method": "recipe.add_favorite", "recipe_id": recipe_id}, method="POST"
        )
        return self._client._mutator_success(payload)

    def delete_favorite_v1(self, recipe_id: str):
        payload = self._client._call(
            {"method": "recipe.delete_favorite", "recipe_id": recipe_id},
            method="DELETE",
        )
        return self._client._mutator_success(payload)

    def get_favorites_v1(self) -> list[RecipesRecipe]:
        payload = self._client._call({"method": "recipe.get_favorites"})
        raw = self._client._unwrap(payload, "recipes", list_key="recipe")
        return [RecipesRecipe.model_validate(r) for r in raw]

    def get_favorites_v2(self) -> list[RecipesRecipe]:
        payload = self._client._call({"method": "recipe.get_favorites.v2"})
        raw = self._client._unwrap(payload, "recipes", list_key="recipe")
        return [RecipesRecipe.model_validate(r) for r in raw]

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
    ) -> list[RecipesRecipe]:
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
        raw = self._client._unwrap(payload, "recipes", list_key="recipe")
        return [RecipesRecipe.model_validate(r) for r in raw]

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
    ) -> list[RecipesRecipe]:
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
        raw = self._client._unwrap(payload, "recipes", list_key="recipe")
        return [RecipesRecipe.model_validate(r) for r in raw]


__all__ = ["RecipesResource"]
