"""Exercises resource — exercise diary entries + exercise type catalog."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class ExercisesResource(BaseResource):
    """Resource methods for the OAS `Exercise Diary` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def entries_commit_day_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_commit_day_v1`."""
        return self._client.exercise_entries_commit_day_v1(*args, **kwargs)

    def entries_get_month_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_get_month_v1`."""
        return self._client.exercise_entries_get_month_v1(*args, **kwargs)

    def entries_get_month_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_get_month_v2`."""
        return self._client.exercise_entries_get_month_v2(*args, **kwargs)

    def entries_get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_get_v1`."""
        return self._client.exercise_entries_get_v1(*args, **kwargs)

    def entries_get_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_get_v2`."""
        return self._client.exercise_entries_get_v2(*args, **kwargs)

    def entries_save_template_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entries_save_template_v1`."""
        return self._client.exercise_entries_save_template_v1(*args, **kwargs)

    def entry_edit_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercise_entry_edit_v1`."""
        return self._client.exercise_entry_edit_v1(*args, **kwargs)

    def list_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercises_get_v1`."""
        return self._client.exercises_get_v1(*args, **kwargs)

    def list_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.exercises_get_v2`."""
        return self._client.exercises_get_v2(*args, **kwargs)
