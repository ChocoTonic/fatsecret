"""Resource wrapper for the OAS ``Foods`` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class FoodsResource(BaseResource):
    """Resource methods for the OAS `Foods` tag.

    Phase 1: pure-delegation over the flat ``foods_*`` / ``food_*``
    methods on :class:`Fatsecret`. Future phases swap delegation for
    OAS-codegen'd implementations.
    """

    def autocomplete_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_autocomplete_v1`."""
        return self._client.foods_autocomplete_v1(*args, **kwargs)

    def autocomplete_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_autocomplete_v2`."""
        return self._client.foods_autocomplete_v2(*args, **kwargs)

    def find_id_for_barcode_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_find_id_for_barcode_v1`."""
        return self._client.food_find_id_for_barcode_v1(*args, **kwargs)

    def find_id_for_barcode_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_find_id_for_barcode_v2`."""
        return self._client.food_find_id_for_barcode_v2(*args, **kwargs)

    def get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_get_v1`."""
        return self._client.food_get_v1(*args, **kwargs)

    def get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_get_v2`."""
        return self._client.food_get_v2(*args, **kwargs)

    def get_v3(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_get_v3`."""
        return self._client.food_get_v3(*args, **kwargs)

    def get_v4(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_get_v4`."""
        return self._client.food_get_v4(*args, **kwargs)

    def get_v5(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_get_v5`."""
        return self._client.food_get_v5(*args, **kwargs)

    def search_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_search_v1`."""
        return self._client.foods_search_v1(*args, **kwargs)

    def search_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_search_v2`."""
        return self._client.foods_search_v2(*args, **kwargs)

    def search_v3(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_search_v3`."""
        return self._client.foods_search_v3(*args, **kwargs)

    def search_v4(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_search_v4`."""
        return self._client.foods_search_v4(*args, **kwargs)

    def search_v5(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.foods_search_v5`."""
        return self._client.foods_search_v5(*args, **kwargs)
