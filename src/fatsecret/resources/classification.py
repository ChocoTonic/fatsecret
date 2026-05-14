"""Resource wrapper for the OAS `Food Classification` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class ClassificationResource(BaseResource):
    """Resource methods for the OAS `Food Classification` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def brands_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_brands_get_v1`."""
        return self._client.food_brands_get_v1(*args, **kwargs)

    def brands_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_brands_get_v2`."""
        return self._client.food_brands_get_v2(*args, **kwargs)

    def categories_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_categories_get_v1`."""
        return self._client.food_categories_get_v1(*args, **kwargs)

    def categories_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_categories_get_v2`."""
        return self._client.food_categories_get_v2(*args, **kwargs)

    def sub_categories_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_sub_categories_get_v1`."""
        return self._client.food_sub_categories_get_v1(*args, **kwargs)

    def sub_categories_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_sub_categories_get_v2`."""
        return self._client.food_sub_categories_get_v2(*args, **kwargs)
