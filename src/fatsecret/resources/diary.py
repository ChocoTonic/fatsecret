"""Food diary resource — food entry CRUD + diary retrieval by day/month."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class DiaryResource(BaseResource):
    """Resource methods for the OAS `Food Diary` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def entries_copy_saved_meal_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_copy_saved_meal_v1`."""
        return self._client.food_entries_copy_saved_meal_v1(*args, **kwargs)

    def entries_copy_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_copy_v1`."""
        return self._client.food_entries_copy_v1(*args, **kwargs)

    def entries_get_month_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_get_month_v1`."""
        return self._client.food_entries_get_month_v1(*args, **kwargs)

    def entries_get_month_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_get_month_v2`."""
        return self._client.food_entries_get_month_v2(*args, **kwargs)

    def entries_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_get_v1`."""
        return self._client.food_entries_get_v1(*args, **kwargs)

    def entries_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entries_get_v2`."""
        return self._client.food_entries_get_v2(*args, **kwargs)

    def entry_create_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entry_create_v1`."""
        return self._client.food_entry_create_v1(*args, **kwargs)

    def entry_delete_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entry_delete_v1`."""
        return self._client.food_entry_delete_v1(*args, **kwargs)

    def entry_edit_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.food_entry_edit_v1`."""
        return self._client.food_entry_edit_v1(*args, **kwargs)
