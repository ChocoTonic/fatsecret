"""Exercise Diary resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

import datetime
from typing import Optional, Union

from ._generated.exercises import ExercisesResource as _GeneratedExercisesResource


class ExercisesResource(_GeneratedExercisesResource):
    """Generated Exercise Diary resource plus a small set of hand-overrides.

    Hand overrides:

      * ``entries_save_template_v1`` — coerce ``days`` to ``int`` so a string
        or float input still results in an integer query value, matching the
        long-standing hand-written behaviour and its passing test suite.
    """

    def entries_save_template_v1(
        self,
        days: int,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ):
        params = {"method": "exercise_entries.save_template", "days": int(days)}
        if date is not None:
            params["date"] = self._client.unix_time_v2(date)
        payload = self._client._call(params, method="POST")
        return self._client._mutator_success(payload)


__all__ = ["ExercisesResource"]
