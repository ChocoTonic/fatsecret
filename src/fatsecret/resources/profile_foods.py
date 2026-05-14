"""Resource methods for the OAS ``Profile Foods`` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class ProfileFoodsResource(BaseResource):
    """Resource methods for the OAS `Profile Foods` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def add_favorite_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_add_favorite_v1`."""
        return self._client.food_add_favorite_v1(*args, **kwargs)

    def create_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_create_v1`."""
        return self._client.food_create_v1(*args, **kwargs)

    def create_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_create_v2`."""
        return self._client.food_create_v2(*args, **kwargs)

    def delete_favorite_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_delete_favorite_v1`."""
        return self._client.food_delete_favorite_v1(*args, **kwargs)

    def get_favorites_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_favorites_v1`."""
        return self._client.foods_get_favorites_v1(*args, **kwargs)

    def get_favorites_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_favorites_v2`."""
        return self._client.foods_get_favorites_v2(*args, **kwargs)

    def get_most_eaten_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_most_eaten_v1`."""
        return self._client.foods_get_most_eaten_v1(*args, **kwargs)

    def get_most_eaten_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_most_eaten_v2`."""
        return self._client.foods_get_most_eaten_v2(*args, **kwargs)

    def get_recently_eaten_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_recently_eaten_v1`."""
        return self._client.foods_get_recently_eaten_v1(*args, **kwargs)

    def get_recently_eaten_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_get_recently_eaten_v2`."""
        return self._client.foods_get_recently_eaten_v2(*args, **kwargs)
