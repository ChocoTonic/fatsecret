"""Food diary resource — food entry CRUD + diary retrieval by day/month."""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union

from ._base import BaseResource


class DiaryResource(BaseResource):
    """Resource methods for the OAS `Food Diary` tag."""

    def entry_create_v1(
        self,
        food_id: str,
        food_entry_name: str,
        serving_id: str,
        number_of_units: float,
        meal: str,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entry.create v1."""
        params = {
            "method": "food_entry.create",
            "food_id": food_id,
            "food_entry_name": food_entry_name,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
            "meal": meal,
        }
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params, method="POST")
        return self._client._unwrap(payload, "food_entries", list_key="food_entry")

    def entry_edit_v1(
        self,
        food_entry_id: str,
        food_entry_name: Optional[str] = None,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
        meal: Optional[str] = None,
    ) -> Union[bool, Any]:
        """food_entry.edit v1."""
        params = {"method": "food_entry.edit", "food_entry_id": food_entry_id}
        self._client._set_optional(
            params,
            [
                ("food_entry_name", food_entry_name),
                ("serving_id", serving_id),
                ("number_of_units", number_of_units),
                ("meal", meal),
            ],
        )
        payload = self._client._call(params, method="PUT")
        return self._client._mutator_success(payload)

    def entry_delete_v1(self, food_entry_id: str) -> Union[bool, Any]:
        """food_entry.delete v1."""
        payload = self._client._call(
            {"method": "food_entry.delete", "food_entry_id": food_entry_id},
            method="DELETE",
        )
        return self._client._mutator_success(payload)

    def entries_get_v1(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get v1 (DEPRECATED upstream). Pass either food_entry_id or date."""
        if food_entry_id is None and date is None:
            return []
        params: dict = {"method": "food_entries.get"}
        if food_entry_id is not None:
            params["food_entry_id"] = food_entry_id
        else:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_entries", list_key="food_entry")

    def entries_get_v2(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get v2 (current). Pass either food_entry_id or date."""
        if food_entry_id is None and date is None:
            return []
        params: dict = {"method": "food_entries.get.v2"}
        if food_entry_id is not None:
            params["food_entry_id"] = food_entry_id
        else:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "food_entries", list_key="food_entry")

    def entries_get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "food_entries.get_month"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")

    def entries_get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get_month v2 (current)."""
        params: dict = {"method": "food_entries.get_month.v2"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")

    def entries_copy_v1(
        self,
        from_date: Union[datetime.datetime, datetime.date, int, float],
        to_date: Union[datetime.datetime, datetime.date, int, float],
        meal: Optional[str] = None,
    ) -> Union[bool, Any]:
        """food_entries.copy v1."""
        params = {
            "method": "food_entries.copy",
            "from_date": self._client.unix_time_v2(from_date),
            "to_date": self._client.unix_time_v2(to_date),
        }
        self._client._set_optional(params, [("meal", meal)])
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)

    def entries_copy_saved_meal_v1(
        self,
        saved_meal_id: str,
        meal: str,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """food_entries.copy_saved_meal v1."""
        params = {
            "method": "food_entries.copy_saved_meal",
            "saved_meal_id": saved_meal_id,
            "meal": meal,
        }
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)
