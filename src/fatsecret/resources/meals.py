"""Saved meals resource — saved_meal CRUD + saved_meals.get + saved_meal_item CRUD + saved_meal_items.get."""

from __future__ import annotations

from typing import Any, Optional, Union

from ._base import BaseResource


class MealsResource(BaseResource):
    """Resource methods for the OAS `Saved Meals` tag."""

    def create_v1(
        self,
        saved_meal_name: str,
        saved_meal_description: Optional[str] = None,
        meals: Optional[str] = None,
    ) -> Any:
        """saved_meal.create v1."""
        params = {"method": "saved_meal.create", "saved_meal_name": saved_meal_name}
        self._client._set_optional(
            params,
            [("saved_meal_description", saved_meal_description), ("meals", meals)],
        )
        payload = self._client._call(params, method="POST")
        return self._client._unwrap(payload, "saved_meal_id")

    def edit_v1(
        self,
        saved_meal_id: str,
        saved_meal_name: Optional[str] = None,
        saved_meal_description: Optional[str] = None,
        meals: Optional[str] = None,
    ) -> Union[bool, Any]:
        """saved_meal.edit v1."""
        params = {"method": "saved_meal.edit", "saved_meal_id": saved_meal_id}
        self._client._set_optional(
            params,
            [
                ("saved_meal_name", saved_meal_name),
                ("saved_meal_description", saved_meal_description),
                ("meals", meals),
            ],
        )
        payload = self._client._call(params, method="PUT")
        return self._client._mutator_success(payload)

    def delete_v1(self, saved_meal_id: str) -> Union[bool, Any]:
        """saved_meal.delete v1."""
        payload = self._client._call(
            {"method": "saved_meal.delete", "saved_meal_id": saved_meal_id},
            method="DELETE",
        )
        return self._client._mutator_success(payload)

    def get_v1(self, meal: Optional[str] = None) -> list:
        """saved_meals.get v1 (DEPRECATED upstream)."""
        params = {"method": "saved_meals.get"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "saved_meals", list_key="saved_meal")

    def get_v2(self, meal: Optional[str] = None) -> list:
        """saved_meals.get v2 (current)."""
        params = {"method": "saved_meals.get.v2"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "saved_meals", list_key="saved_meal")

    def item_add_v1(
        self,
        saved_meal_id: str,
        food_id: str,
        saved_meal_item_name: str,
        serving_id: str,
        number_of_units: float,
    ) -> Any:
        """saved_meal_item.add v1."""
        params = {
            "method": "saved_meal_item.add",
            "saved_meal_id": saved_meal_id,
            "food_id": food_id,
            "saved_meal_item_name": saved_meal_item_name,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
        }
        payload = self._client._call(params, method="POST")
        return self._client._unwrap(payload, "saved_meal_item_id")

    def item_edit_v1(
        self,
        saved_meal_item_id: str,
        saved_meal_item_name: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """saved_meal_item.edit v1."""
        params = {
            "method": "saved_meal_item.edit",
            "saved_meal_item_id": saved_meal_item_id,
        }
        self._client._set_optional(
            params,
            [
                ("saved_meal_item_name", saved_meal_item_name),
                ("number_of_units", number_of_units),
            ],
        )
        payload = self._client._call(params, method="PUT")
        return self._client._mutator_success(payload)

    def item_delete_v1(self, saved_meal_item_id: str) -> Union[bool, Any]:
        """saved_meal_item.delete v1."""
        payload = self._client._call(
            {
                "method": "saved_meal_item.delete",
                "saved_meal_item_id": saved_meal_item_id,
            },
            method="DELETE",
        )
        return self._client._mutator_success(payload)

    def items_get_v1(self, saved_meal_id: str) -> list:
        """saved_meal_items.get v1 (DEPRECATED upstream)."""
        payload = self._client._call(
            {"method": "saved_meal_items.get", "saved_meal_id": saved_meal_id}
        )
        return self._client._unwrap(
            payload, "saved_meal_items", list_key="saved_meal_item"
        )

    def items_get_v2(self, saved_meal_id: str) -> list:
        """saved_meal_items.get v2 (current)."""
        payload = self._client._call(
            {"method": "saved_meal_items.get.v2", "saved_meal_id": saved_meal_id}
        )
        return self._client._unwrap(
            payload, "saved_meal_items", list_key="saved_meal_item"
        )
