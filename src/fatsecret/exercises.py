class ExercisesMixin:

    def exercises_get(self):
        """This is a utility method, returning the full list of all supported exercise type names and
        their associated unique identifiers.
        """

        params = {"method": "exercises.get", "format": "json"}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_commit_day(self, date=None):
        """Saves the default exercise entries for the user on a nominated date.

        :param date: Date to save default exercises on (default value is the current day).
        :type date: datetime.datetime
        """

        params = {"method": "exercise_entries.commit_day", "format": "json"}

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_get(self, date=None):
        """Returns the daily exercise entries for the user on a nominated date.

        The API will always return 24 hours worth of exercise entries for a given user on a given date.
        These entries will either be "template" entries (which a user may override for any given day of the week)
        or saved exercise entry values.

        :param date: Day of exercises to retrieve (default value is the current day).
        :type date: datetime.datetime
        """

        params = {"method": "exercise_entries.get", "format": "json"}

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_get_month(self, date=None):
        """Returns the summary estimated daily calories expended for a user's exercise diary entries for
        the month specified. Use this call to display total energy expenditure information to users about their
        exercise and activities for a nominated month.

        :param date: Day within month to retrieve (default value is the current day for the current month).
        :type date: datetime.datetime
        """

        params = {"method": "exercise_entries.get_month", "format": "json"}

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entries_save_template(self, days, date=None):
        """Takes the set of exercise entries on a nominated date and saves these entries as "template"
        entries for nominated days of the week.

        :param days: The days of the week specified as bits with Sunday being the 1st bit and Saturday being the
            last. For example Tuesday and Thursday would be represented as 00010100 in bits where Tuesday is the 3rd
            bit from the right and Thursday being the 5th.
        :type days: str
        :param date: Day of exercises to use as the template (default value is the current day).
        :type date: datetime.datetime
        """
        params = {
            "method": "exercise_entries.get_month",
            "format": "json",
            "days": int(days),
        }

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def exercise_entry_edit(
        self,
        shift_to_id,
        shift_from_id,
        minutes,
        date=None,
        shift_to_name=None,
        shift_from_name=None,
        kcals=None,
    ):
        """Records a change to a user's exercise diary entry for a nominated date.

        All changes to an exercise diary involve either increasing the duration of an existing activity or
        introducing a new activity for a nominated duration. Because there are always 24 hours worth of exercise
        entries on any given date, the user must nominate the exercise or activity from which the time was taken
        to balance out the total duration of activities and exercises for the 24 hour period. As such, each change
        to the exercise entries on a given day is a "shifting" operation where time is moved from one activity to
        another. An exercise is removed from the day when all of the time allocated to it is shifted to other exercises.

        :param shift_to_id: The ID of the exercise type to shift to.
        :type shift_to_id: str
        :param shift_from_id: The ID of the exercise type to shift from.
        :type shift_from_id: str
        :param minutes: The number of minutes to shift.
        :type minutes: int
        :param date: Day to edit (default value is the current day).
        :type date: datetime.datetime
        :param shift_to_name: Only required if shift_to_id is 0 (exercise type "Other").
            This is the name of the new custom exercise type to shift to.
        :type shift_to_name: str
        :param shift_from_name: Only required if shift_from_id is 0 (exercise type "Other").
            This is the name of the custom exercise type to shift from.
        :type shift_from_name: str
        :param kcals: Number of calories burned
        :type kcals: int
        """

        params = {
            "method": "exercise_entry.edit",
            "format": "json",
            "shift_to_id": shift_to_id,
            "shift_from_id": shift_from_id,
            "minutes": minutes,
        }

        if date:
            params["date"] = self.unix_time(date)

        if shift_to_id == 0:
            if shift_to_name:
                params["shift_to_name"] = shift_to_name
            elif kcals:
                params["kcals"] = kcals
            else:
                return
        if shift_from_id == 0:
            if shift_from_name:
                params["shift_from_name"] = shift_from_name
            else:
                return

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
