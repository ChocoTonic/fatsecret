"""Saved meals resource — saved_meal CRUD + saved_meals.get + saved_meal_item CRUD + saved_meal_items.get."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class MealsResource(BaseResource):
    """Resource methods for the OAS `Saved Meals` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def create_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_create_v1`."""
        return self._client.saved_meal_create_v1(*args, **kwargs)

    def delete_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_delete_v1`."""
        return self._client.saved_meal_delete_v1(*args, **kwargs)

    def edit_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_edit_v1`."""
        return self._client.saved_meal_edit_v1(*args, **kwargs)

    def get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meals_get_v1`."""
        return self._client.saved_meals_get_v1(*args, **kwargs)

    def get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meals_get_v2`."""
        return self._client.saved_meals_get_v2(*args, **kwargs)

    def item_add_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_item_add_v1`."""
        return self._client.saved_meal_item_add_v1(*args, **kwargs)

    def item_delete_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_item_delete_v1`."""
        return self._client.saved_meal_item_delete_v1(*args, **kwargs)

    def item_edit_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_item_edit_v1`."""
        return self._client.saved_meal_item_edit_v1(*args, **kwargs)

    def items_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_items_get_v1`."""
        return self._client.saved_meal_items_get_v1(*args, **kwargs)

    def items_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.saved_meal_items_get_v2`."""
        return self._client.saved_meal_items_get_v2(*args, **kwargs)
