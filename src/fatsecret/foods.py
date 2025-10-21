class FoodsMixin:

    def food_add_favorite(self, food_id, serving_id=None, number_of_units=None):
        """Add a food to a user's favorite according to the parameters specified.

        :param food_id: The ID of the favorite food to add.
        :type food_id: str
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :type serving_id: str
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        :type number_of_units: float
        """

        params = {"method": "food.add_favorite", "format": "json", "food_id": food_id}

        if serving_id and number_of_units:
            params["serving_id"] = serving_id
            params["number_of_units"] = number_of_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_delete_favorite(self, food_id, serving_id=None, number_of_units=None):
        """Delete the food to a user's favorite according to the parameters specified.

        :param food_id: The ID of the favorite food to add.
        :type food_id: str
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :type serving_id: str
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        :type number_of_units: float
        """

        params = {
            "method": "food.delete_favorite",
            "format": "json",
            "food_id": food_id,
        }

        if serving_id and number_of_units:
            params["serving_id"] = serving_id
            params["number_of_units"] = number_of_units

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_get(self, food_id):
        """Returns detailed nutritional information for the specified food.

        Use this call to display nutrition values for a food to users.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """

        params = {"method": "food.get", "food_id": food_id, "format": "json"}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_get_v2(self, food_id, region=None, language=None):
        """Returns detailed nutritional information for the specified food.

        Use this call to display nutrition values for a food to users.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """

        params = {"method": "food.get.v2", "food_id": food_id, "format": "json"}

        if region:
            params["region"] = region

        if language:
            params["language"] = language

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_find_id_for_barcode(self, barcode, region=None, language=None):
        """Returns the food_id matching the barcode specified.

        Barcodes must be specified as GTIN-13 numbers - a 13-digit number filled in with
        zeros for the spaces to the left.

        UPC-A, EAN-13 and EAN-8 barcodes may be specified.

        UPC-E barcodes should be converted to their UPC-A equivalent (and then specified
        as GTIN-13 numbers).

        :param barcode: The 13-digit GTIN-13 formated sequence of digits representing
        the barcode to search against.
        :type food_id: str
        """

        params = {
            "method": "food.find_id_for_barcode",
            "barcode": barcode,
            "format": "json",
        }

        if region:
            params["region"] = region

        if language:
            params["language"] = language

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_favorites(self):
        """Returns the favorite foods for the authenticated user."""

        params = {"method": "foods.get_favorites", "format": "json"}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_most_eaten(self, meal=None):
        """Returns the most eaten foods for the user according to the meal specified.

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        params = {"method": "foods.get_most_eaten", "format": "json"}

        if meal in ["breakfast", "lunch", "dinner", "other"]:
            params["meal"] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_get_recently_eaten(self, meal=None):
        """Returns the recently eaten foods for the user according to the meal specified

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        params = {"method": "foods.get_recently_eaten", "format": "json"}

        if meal in ["breakfast", "lunch", "dinner", "other"]:
            params["meal"] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_search(
        self,
        search_expression,
        page_number=None,
        max_results=None,
        region=None,
        language=None,
    ):
        """Conducts a search of the food database using the search expression specified.

        The results are paginated according to a zero-based "page" offset. Successive pages of results
        may be retrieved by specifying a starting page offset value. For instance, specifying a max_results
        of 10 and page_number of 4 will return results numbered 41-50.

        :param search_expression: term or phrase to search
        :type search_expression: str
        :param page_number: page set to return (default 0)
        :type page_number: int
        :param max_results: total results per page (default 20)
        :type max_results: int
        """
        params = {
            "method": "foods.search",
            "search_expression": search_expression,
            "format": "json",
        }

        if page_number and max_results:
            params["page_number"] = page_number
            params["max_results"] = max_results

        if region:
            params["region"] = region

        if language:
            params["language"] = language

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def foods_autocomplete(
        self, expression, max_results=None, region=None, language=None
    ):
        """Returns a list of suggestions for the expression specified.

        :param expression:
            Suggestions for the given expression is returned. E.G.: "chic" will return
            up to four of the best suggestions that contains "chic".
        :type expression: str
        :param page_number: page set to return (default 0)
        :type max_results: int
        """
        params = {
            "method": "foods.autocomplete",
            "expression": expression,
            "format": "json",
        }

        if max_results:
            params["max_results"] = max_results

        if region:
            params["region"] = region

        if language:
            params["language"] = language

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    # profile

    def food_entries_copy(self, from_date, to_date, meal=None):
        """Copies the food entries for a specified meal from a nominated date to a nominated date.

        :param from_date: The date to copy food entries from
        :type from_date: datetime.datetime
        :param to_date: The date to copy food entries to (default value is the current day).
        :type to_date: datetime.datetime
        :param meal: The type of meal to copy. Valid meal types are "breakfast", "lunch", "dinner" and "other"
            (default value is all).
        :type meal: str
        """

        params = {
            "method": "food_entries.copy",
            "format": "json",
            "from_date": self.unix_time(from_date),
            "to_date": self.unix_time(to_date),
        }

        if meal:
            params["meal"] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_copy_saved_meal(self, meal_id, meal, date=None):
        """Copies the food entries for a specified saved meal to a specified meal.

        :param meal_id: The ID of the saved meal
        :type meal_id: str
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        :param date: Day to copy meal to. (default value is the current day).
        :type date: datetime.datetime
        """

        params = {
            "method": "food_entries.copy_saved_meal",
            "format": "json",
            "saved_meal_id": meal_id,
            "meal": meal,
        }

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_get(self, food_entry_id=None, date=None):
        """Returns saved food diary entries for the user according to the filter specified.

        This method can be used to return all food diary entries recorded on a nominated date or a single food
        diary entry with a nominated food_entry_id.

        :: You must specify either date or food_entry_id.

        :param food_entry_id: The ID of the food entry to retrieve. You must specify either date or food_entry_id.
        :type food_entry_id: str
        :param date: Day to filter food entries by (default value is the current day).
        :type date: datetime.datetmie
        """

        params = {"method": "food_entries.get", "format": "json"}

        if food_entry_id:
            params["food_entry_id"] = food_entry_id
        elif date:
            params["date"] = self.unix_time(date)
        else:
            return  # exit without running as no valid parameter was provided

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entries_get_month(self, date=None):
        """Returns summary daily nutritional information for a user's food diary entries for the month specified.

        Use this call to display nutritional information to users about their food intake for a nominated month.

        :param date: Day in the month to return (default value is the current day to get current month).
        :type date: datetime.datetime
        """

        params = {"method": "food_entries.get_month", "format": "json"}

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_create(
        self, food_id, food_entry_name, serving_id, number_of_units, meal, date=None
    ):
        """Records a food diary entry for the user according to the parameters specified.

        :param food_id: The ID of the food eaten.
        :type food_id: str
        :param food_entry_name: The name of the food entry.
        :type food_entry_name: str
        :param serving_id: The ID of the serving
        :type serving_id: str
        :param number_of_units: The number of servings eaten.
        :type number_of_units: float
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        :param date: Day to create food entry on (default value is the current day).
        :type date: datetime.datetime
        """

        params = {
            "method": "food_entry.create",
            "format": "json",
            "food_id": food_id,
            "food_entry_name": food_entry_name,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
            "meal": meal,
        }

        if date:
            params["date"] = self.unix_time(date)

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_delete(self, food_entry_id):
        """Deletes the specified food entry for the user.

        :param food_entry_id: The ID of the food entry to delete.
        :type food_entry_id: str
        """

        params = {
            "method": "food_entry.delete",
            "format": "json",
            "food_entry_id": food_entry_id,
        }

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_entry_edit(
        self, food_entry_id, entry_name=None, serving_id=None, num_units=None, meal=None
    ):
        """Adjusts the recorded values for a food diary entry.

        Note that the date of the entry may not be adjusted, however one or more of the other remaining
        properties - food_entry_name, serving_id, number_of_units, or meal may be altered. In order to shift
        the date for which a food diary entry was recorded the original entry must be deleted and a new entry recorded.

        :param food_entry_id: The ID of the food entry to edit.
        :type food_entry_id: str
        :param entry_name: The new name of the food entry.
        :type entry_name: str
        :param serving_id: The new ID of the serving to change to.
        :type serving_id: str
        :param num_units: The new number of servings eaten.
        :type num_units: float
        :param meal: The new type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        """

        params = {
            "method": "food_entry.edit",
            "food_entry_id": food_entry_id,
            "format": "json",
        }

        if entry_name:
            params["food_entry_name"] = entry_name

        if serving_id:
            params["serving_id"] = serving_id

        if num_units:
            params["number_of_units"] = num_units

        if meal:
            params["meal"] = meal

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
