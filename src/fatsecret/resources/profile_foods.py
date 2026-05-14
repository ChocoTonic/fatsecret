"""Resource methods for the OAS ``Profile Foods`` tag."""

from __future__ import annotations

from typing import Any, Optional, Union

from ._base import BaseResource


class ProfileFoodsResource(BaseResource):
    """Resource methods for the OAS `Profile Foods` tag."""

    def create_v1(
        self,
        brand_name: str,
        food_name: str,
        serving_size: str,
        calories: float,
        fat: float,
        carbohydrate: float,
        protein: float,
        brand_type: Optional[str] = None,
        serving_amount: Optional[str] = None,
        serving_amount_unit: Optional[str] = None,
        calories_from_fat: Optional[float] = None,
        saturated_fat: Optional[float] = None,
        polyunsaturated_fat: Optional[float] = None,
        monounsaturated_fat: Optional[float] = None,
        trans_fat: Optional[float] = None,
        cholesterol: Optional[float] = None,
        sodium: Optional[float] = None,
        potassium: Optional[float] = None,
        fiber: Optional[float] = None,
        sugar: Optional[float] = None,
        other_carbohydrate: Optional[float] = None,
        vitamin_a: Optional[float] = None,
        vitamin_c: Optional[float] = None,
        calcium: Optional[float] = None,
        iron: Optional[float] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.create v1 (DEPRECATED upstream). Premier-exclusive. OAuth1 only.

        v1 takes vitamin_a/c, calcium, iron as %DV.
        """
        params = {
            "method": "food.create",
            "brand_name": brand_name,
            "food_name": food_name,
            "serving_size": serving_size,
            "calories": calories,
            "fat": fat,
            "carbohydrate": carbohydrate,
            "protein": protein,
        }
        self._client._set_optional(
            params,
            [
                ("brand_type", brand_type),
                ("serving_amount", serving_amount),
                ("serving_amount_unit", serving_amount_unit),
                ("calories_from_fat", calories_from_fat),
                ("saturated_fat", saturated_fat),
                ("polyunsaturated_fat", polyunsaturated_fat),
                ("monounsaturated_fat", monounsaturated_fat),
                ("trans_fat", trans_fat),
                ("cholesterol", cholesterol),
                ("sodium", sodium),
                ("potassium", potassium),
                ("fiber", fiber),
                ("sugar", sugar),
                ("other_carbohydrate", other_carbohydrate),
                ("vitamin_a", vitamin_a),
                ("vitamin_c", vitamin_c),
                ("calcium", calcium),
                ("iron", iron),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params, method="POST")
        return self._client._unwrap(payload, "food_id")

    def create_v2(
        self,
        brand_name: str,
        food_name: str,
        serving_size: str,
        calories: float,
        fat: float,
        carbohydrate: float,
        protein: float,
        brand_type: Optional[str] = None,
        serving_amount: Optional[str] = None,
        serving_amount_unit: Optional[str] = None,
        calories_from_fat: Optional[float] = None,
        saturated_fat: Optional[float] = None,
        polyunsaturated_fat: Optional[float] = None,
        monounsaturated_fat: Optional[float] = None,
        trans_fat: Optional[float] = None,
        cholesterol: Optional[float] = None,
        sodium: Optional[float] = None,
        potassium: Optional[float] = None,
        fiber: Optional[float] = None,
        sugar: Optional[float] = None,
        added_sugars: Optional[float] = None,
        vitamin_d: Optional[float] = None,
        vitamin_a: Optional[float] = None,
        vitamin_c: Optional[float] = None,
        calcium: Optional[float] = None,
        iron: Optional[float] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.create v2 (current). Premier-exclusive. OAuth1 only.

        v2 takes raw nutrient values; adds added_sugars and vitamin_d.
        """
        params = {
            "method": "food.create.v2",
            "brand_name": brand_name,
            "food_name": food_name,
            "serving_size": serving_size,
            "calories": calories,
            "fat": fat,
            "carbohydrate": carbohydrate,
            "protein": protein,
        }
        self._client._set_optional(
            params,
            [
                ("brand_type", brand_type),
                ("serving_amount", serving_amount),
                ("serving_amount_unit", serving_amount_unit),
                ("calories_from_fat", calories_from_fat),
                ("saturated_fat", saturated_fat),
                ("polyunsaturated_fat", polyunsaturated_fat),
                ("monounsaturated_fat", monounsaturated_fat),
                ("trans_fat", trans_fat),
                ("cholesterol", cholesterol),
                ("sodium", sodium),
                ("potassium", potassium),
                ("fiber", fiber),
                ("sugar", sugar),
                ("added_sugars", added_sugars),
                ("vitamin_d", vitamin_d),
                ("vitamin_a", vitamin_a),
                ("vitamin_c", vitamin_c),
                ("calcium", calcium),
                ("iron", iron),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._client._call(params, method="POST")
        return self._client._unwrap(payload, "food_id")

    def add_favorite_v1(
        self,
        food_id: str,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """food.add_favorite v1."""
        params = {"method": "food.add_favorite", "food_id": food_id}
        self._client._set_optional(
            params, [("serving_id", serving_id), ("number_of_units", number_of_units)]
        )
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)

    def delete_favorite_v1(
        self,
        food_id: str,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """food.delete_favorite v1."""
        params = {"method": "food.delete_favorite", "food_id": food_id}
        self._client._set_optional(
            params, [("serving_id", serving_id), ("number_of_units", number_of_units)]
        )
        payload = self._client._call(params, method="DELETE")
        return self._client._mutator_success(payload)

    def get_favorites_v1(self) -> list:
        """foods.get_favorites v1 (DEPRECATED upstream)."""
        payload = self._client._call({"method": "foods.get_favorites"})
        return self._client._unwrap(payload, "foods", list_key="food")

    def get_favorites_v2(self) -> list:
        """foods.get_favorites v2 (current)."""
        payload = self._client._call({"method": "foods.get_favorites.v2"})
        return self._client._unwrap(payload, "foods", list_key="food")

    def get_most_eaten_v1(self, meal: Optional[str] = None) -> list:
        """foods.get_most_eaten v1 (DEPRECATED upstream)."""
        params = {"method": "foods.get_most_eaten"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods", list_key="food")

    def get_most_eaten_v2(self, meal: Optional[str] = None) -> list:
        """foods.get_most_eaten v2 (current)."""
        params = {"method": "foods.get_most_eaten.v2"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods", list_key="food")

    def get_recently_eaten_v1(self, meal: Optional[str] = None) -> list:
        """foods.get_recently_eaten v1 (DEPRECATED upstream)."""
        params = {"method": "foods.get_recently_eaten"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods", list_key="food")

    def get_recently_eaten_v2(self, meal: Optional[str] = None) -> list:
        """foods.get_recently_eaten v2 (current). Premier per spec."""
        params = {"method": "foods.get_recently_eaten.v2"}
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "foods", list_key="food")
