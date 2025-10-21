class MealsMixin:

    def saved_meal_create(self, meal_name, meal_desc=None, meals=None):
        """Records a saved meal for the user according to the parameters specified.

        :param meal_name: The name of the saved meal.
        :type meal_name: str
        :param meal_desc: A short description of the saved meal.
        :type meal_desc: str
        :param meals: A comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meals: list
        """

        params = {
            "method": "saved_meal.create",
            "format": "json",
            "saved_meal_name": meal_name,
        }
        if meal_desc:
            params["saved_meal_description"] = meal_desc
        if meals:
            params["meals"] = ",".join(meals)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_delete(self, meal_id):
        """Deletes the specified saved meal for the user.

        :param meal_id: The ID of the saved meal to delete.
        :type meal_id: str
        """

        params = {
            "method": "saved_meal.delete",
            "format": "json",
            "saved_meal_id": meal_id,
        }

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_edit(self, meal_id, new_name=None, meal_desc=None, meals=None):
        """Records a change to a user's saved meal.

        :param meal_id: The ID of the food entry to edit.
        :type meal_id: str
        :param new_name: The new name of the saved meal.
        :type new_name: str
        :param meal_desc: The new description of the saved meal.
        :type meal_desc: str
        :param meals: The new comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meals: str
        """

        params = {
            "method": "saved_meal.edit",
            "format": "json",
            "saved_meal_id": meal_id,
        }

        if new_name:
            params["saved_meal_name"] = new_name
        if meal_desc:
            params["saved_meal_description"] = meal_desc
        if meals:
            params["meals"] = ",".join(meals)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_get(self, meal=None):
        """Returns saved meals for the authenticated user

        :param meal: Filter result set to 'Breakfast', 'Lunch', 'Dinner', or 'Other'
        :type meal: str
        """

        params = {"method": "saved_meals.get", "format": "json"}

        if meal:
            params["meal"] = meal

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_add(
        self, meal_id, food_id, food_entry_name, serving_id, num_units
    ):
        """Adds a food to a user's saved meal according to the parameters specified.

        :param meal_id: The ID of the saved meal.
        :type meal_id: str
        :param food_id: The ID of the food to add to the saved meal.
        :type food_id: str
        :param food_entry_name: The name of the food to add to the saved meal.
        :type food_entry_name: str
        :param serving_id: The ID of the serving of the food to add to the saved meal.
        :type serving_id: str
        :param num_units: The number of servings of the food to add to the saved meal.
        :type num_units: float
        """
        params = {
            "method": "saved_meal_item.add",
            "format": "json",
            "saved_meal_id": meal_id,
            "food_id": food_id,
            "food_entry_name": food_entry_name,
            "serving_id": serving_id,
            "number_of_units": num_units,
        }

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_delete(self, meal_item_id):
        """Deletes the specified saved meal item for the user.

        :param meal_item_id: The ID of the saved meal item to delete.
        :type meal_item_id: str
        """

        params = {
            "method": "saved_meal_item.delete",
            "format": "json",
            "saved_meal_item_id": meal_item_id,
        }

        response = self.session.get(self.api_url, params)
        return self.valid_response(response)

    def saved_meal_item_edit(self, meal_item_id, item_name=None, num_units=None):
        """Records a change to a user's saved meal item.

        Note that the serving_id of the saved meal item may not be adjusted, however one or more of the other
        remaining properties - saved_meal_item_name or number_of_units may be altered. In order to adjust a
        serving_id for which a saved_meal_item was recorded the original item must be deleted and a new item recorded.

        :param meal_item_id: The ID of the saved meal item to edit.
        :type meal_item_id: str
        :param item_name: The new name of the saved meal item.
        :type item_name: str
        :param num_units: The new number of servings of the saved meal item.
        :type num_units: float
        """

        params = {
            "method": "saved_meal_item.edit",
            "format": "json",
            "saved_meal_item_id": meal_item_id,
        }

        if item_name:
            params["saved_meal_item_name"] = item_name
        if num_units:
            params["number_of_units"] = num_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def saved_meal_items_get(self, meal_id):
        """Returns saved meal items for a specified saved meal.

        :param meal_id: The ID of the saved meal to retrieve the saved_meal_items for.
        :type meal_id: str
        """

        params = {
            "method": "saved_meal_items.get",
            "format": "json",
            "saved_meal_id": meal_id,
        }

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
