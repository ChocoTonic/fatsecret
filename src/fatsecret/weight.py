class WeightMixin:

    def weight_update(
        self,
        current_weight_kg,
        date=None,
        weight_type="kg",
        height_type="cm",
        goal_weight_kg=None,
        current_height_cm=None,
        comment=None,
    ):
        """Records a user's weight for a nominated date.

        First time weigh-ins require the goal_weight_kg and current_height_cm parameters.

        :param current_weight_kg: The current weight of the user in kilograms.
        :type current_weight_kg: float
        :param date: Day to for weight record (default value is the current day).
        :type date: datetime.datetime
        :param weight_type: The weight measurement type for this user profile. Valid types are "kg" and "lb"
        :type weight_type: str
        :param height_type: The height measurement type for this user profile. Valid types are "cm" and "inch"
        :type height_type: str
        :param goal_weight_kg: The goal weight of the user in kilograms. This is required for the first weigh-in.
        :type goal_weight_kg: float
        :param current_height_cm: The current height of the user in centimetres. This is required for the first
            weigh-in. You can only set this for the first time (subsequent updates will not change a user's height)
        :type current_height_cm: float
        :param comment: A comment for this weigh-in.
        :type comment: str
        """

        params = {
            "method": "weight.update",
            "format": "json",
            "current_weight_kg": current_weight_kg,
            "weight_type": weight_type,
            "height_type": height_type,
        }

        if date:
            params["date"] = self.unix_time(date)
        if goal_weight_kg:
            params["goal_weight_kg"] = goal_weight_kg
        if current_height_cm:
            params["current_height_cm"] = current_height_cm
        if comment:
            params["comment"] = comment

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def weights_get_month(self, date=None):
        """Returns the recorded weights for a user for the month specified. Use this call to display a user's
        weight chart or log of weight changes for a nominated month.

        :param date: Day within month to return (default value is the current day for the current month).
        :type date: datetime.datetime
        """

        params = {"method": "weights.get_month", "format": "json"}

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
