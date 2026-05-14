"""Recipes resource — recipe.get, recipes.search, recipe_types.get, recipe favorites."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class RecipesResource(BaseResource):
    """Resource methods for the OAS `Recipes` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def add_favorite_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_add_favorite_v1`."""
        return self._client.recipe_add_favorite_v1(*args, **kwargs)

    def delete_favorite_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_delete_favorite_v1`."""
        return self._client.recipe_delete_favorite_v1(*args, **kwargs)

    def get_favorites_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipes_get_favorites_v1`."""
        return self._client.recipes_get_favorites_v1(*args, **kwargs)

    def get_favorites_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipes_get_favorites_v2`."""
        return self._client.recipes_get_favorites_v2(*args, **kwargs)

    def get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_get_v1`."""
        return self._client.recipe_get_v1(*args, **kwargs)

    def get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_get_v2`."""
        return self._client.recipe_get_v2(*args, **kwargs)

    def search_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipes_search_v1`."""
        return self._client.recipes_search_v1(*args, **kwargs)

    def search_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipes_search_v2`."""
        return self._client.recipes_search_v2(*args, **kwargs)

    def search_v3(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipes_search_v3`."""
        return self._client.recipes_search_v3(*args, **kwargs)

    def types_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_types_get_v1`."""
        return self._client.recipe_types_get_v1(*args, **kwargs)

    def types_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.recipe_types_get_v2`."""
        return self._client.recipe_types_get_v2(*args, **kwargs)
