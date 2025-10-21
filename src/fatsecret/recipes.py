class RecipesMixin:

    def recipes_add_favorite(self, recipe_id):
        """Add a recipe to a user's favorite.

        :param recipe_id: The ID of the favorite recipe to add.
        :type recipe_id: str
        """

        params = {
            "method": "recipes.add_favorites",
            "format": "json",
            "recipe_id": recipe_id,
        }

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_delete_favorite(self, recipe_id):
        """Delete a recipe to a user's favorite.

        :param recipe_id: The ID of the favorite recipe to delete.
        :type recipe_id: str
        """

        params = {
            "method": "recipes.delete_favorites",
            "format": "json",
            "recipe_id": recipe_id,
        }

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipe_get(self, recipe_id):
        """Returns detailed information for the specified recipe.

        :param recipe_id: Fatsecret ID of desired recipe
        :type recipe_id: str
        """

        params = {"method": "recipe.get", "format": "json", "recipe_id": recipe_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_get_favorites(self):
        """Returns the favorite recipes for the specified user."""

        params = {"method": "recipes.get_favorites", "format": "json"}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipes_search(
        self, search_expression, recipe_type=None, page_number=None, max_results=None
    ):
        """Conducts a search of the recipe database using the search expression specified.

        The results are paginated according to a zero-based "page" offset. Successive pages of results may be
        retrieved by specifying a starting page offset value. For instance, specifying a max_results of 10 and
        page_number of 4 will return results numbered 41-50.

        :param search_expression: phrase to search on
        :type search_expression: str
        :param recipe_type: type of recipe to filter
        :type recipe_type: str
        :param page_number: result page to return (default 0)
        :type page_number: int
        :param max_results: total results per page to return (default 20)
        :type max_results: int
        """

        params = {
            "method": "recipes.search",
            "search_expression": search_expression,
            "format": "json",
        }

        if recipe_type:
            params["recipe_type"] = recipe_type
        if page_number and max_results:
            params["page_number"] = page_number
            params["max_results"] = max_results

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def recipe_types_get(self):
        """This is a utility method, returning the full list of all supported recipe type names."""

        params = {"method": "recipe_types.get", "format": "json"}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
