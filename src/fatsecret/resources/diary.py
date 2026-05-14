"""Food Diary resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

import datetime
from typing import Optional, Union

from ._generated.diary import DiaryResource as _GeneratedDiaryResource


class DiaryResource(_GeneratedDiaryResource):
    """Generated Food Diary resource plus a small set of hand-overrides.

    Hand overrides:

      * ``entries_get_v1`` / ``entries_get_v2`` — short-circuit to ``[]`` when
        neither ``food_entry_id`` nor ``date`` is supplied.  The upstream API
        would otherwise reject the call; the wrapper has done this guard
        forever and the test suite asserts it.
    """

    def entries_get_v1(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ):
        if food_entry_id is None and date is None:
            return []
        return super().entries_get_v1(food_entry_id=food_entry_id, date=date)

    def entries_get_v2(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ):
        if food_entry_id is None and date is None:
            return []
        return super().entries_get_v2(food_entry_id=food_entry_id, date=date)


__all__ = ["DiaryResource"]
