"""Exercises resource — exercise diary entries + exercise type catalog."""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union

from ._base import BaseResource


class ExercisesResource(BaseResource):
    """Resource methods for the OAS `Exercise Diary` tag."""

    def list_v1(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """exercises.get v1 (DEPRECATED upstream)."""
        params = {"method": "exercises.get"}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "exercise_types", list_key="exercise")

    def list_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """exercises.get v2 (current). Region/language are Premier-exclusive."""
        params = {"method": "exercises.get.v2"}
        self._client._set_optional(params, [("region", region), ("language", language)])
        payload = self._client._call(params)
        return self._client._unwrap(payload, "exercise_types", list_key="exercise")

    def entry_edit_v1(
        self,
        shift_to_id: str,
        shift_from_id: str,
        minutes: int,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
        shift_to_name: Optional[str] = None,
        shift_from_name: Optional[str] = None,
        kcal: Optional[int] = None,
    ) -> Union[bool, Any]:
        """exercise_entry.edit v1. Shifts time between activities while maintaining 24h balance."""
        params = {
            "method": "exercise_entry.edit",
            "shift_to_id": shift_to_id,
            "shift_from_id": shift_from_id,
            "minutes": minutes,
        }
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        self._client._set_optional(
            params,
            [
                ("shift_to_name", shift_to_name),
                ("shift_from_name", shift_from_name),
                ("kcal", kcal),
            ],
        )
        payload = self._client._call(params, method="PUT")
        return self._client._mutator_success(payload)

    def entries_get_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get v1 (DEPRECATED upstream)."""
        params: dict = {"method": "exercise_entries.get"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "exercise_entries", list_key="exercise_entry")

    def entries_get_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get v2 (current)."""
        params: dict = {"method": "exercise_entries.get.v2"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "exercise_entries", list_key="exercise_entry")

    def entries_get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "exercise_entries.get_month"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")

    def entries_get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get_month v2 (current)."""
        params: dict = {"method": "exercise_entries.get_month.v2"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")

    def entries_commit_day_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """exercise_entries.commit_day v1."""
        params: dict = {"method": "exercise_entries.commit_day"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)

    def entries_save_template_v1(
        self,
        days: int,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """exercise_entries.save_template v1. Fixes the legacy bug that hit `exercise_entries.get_month`."""
        params = {"method": "exercise_entries.save_template", "days": int(days)}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)
