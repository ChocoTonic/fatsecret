"""Resource wrapper for the OAS `Weight` tag."""

from __future__ import annotations

import datetime
from typing import Any, Optional, Union

from ._base import BaseResource


class WeightResource(BaseResource):
    """Resource methods for the OAS `Weight` tag."""

    def update_v1(
        self,
        current_weight_kg: float,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
        weight_type: Optional[str] = None,
        height_type: Optional[str] = None,
        goal_weight_kg: Optional[float] = None,
        current_height_cm: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> Union[bool, Any]:
        """weight.update v1. First-time entries require goal_weight_kg and current_height_cm."""
        params = {"method": "weight.update", "current_weight_kg": current_weight_kg}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        self._client._set_optional(
            params,
            [
                ("weight_type", weight_type),
                ("height_type", height_type),
                ("goal_weight_kg", goal_weight_kg),
                ("current_height_cm", current_height_cm),
                ("comment", comment),
            ],
        )
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)

    def get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """weights.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "weights.get_month"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")

    def get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """weights.get_month v2 (current)."""
        params: dict = {"method": "weights.get_month.v2"}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params)
        return self._client._unwrap(payload, "month", list_key="day")
