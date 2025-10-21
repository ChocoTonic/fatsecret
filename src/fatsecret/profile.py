class ProfileMixin:

    def profile_create(self, user_id=None):
        """Creates a new profile and returns the oauth_token and oauth_secret for the new profile.

        The token and secret returned by this method are persisted indefinitely and may be used in order to
        provide profile-specific information storage for users including food and exercise diaries and weight tracking.

        :param user_id: You can set your own ID for the newly created profile if you do not wish to store the
            auth_token and auth_secret. Particularly useful if you are only using the FatSecret JavaScript API.
            Use profile.get_auth to retrieve auth_token and auth_secret.
        :type user_id: str
        """

        params = {"method": "profile.create", "format": "json"}

        if user_id:
            params["user_id"] = user_id

        response = self.session.get(self.api_url, params=params)

        return self.valid_response(response)

    def profile_get(self):
        """Returns general status information for a nominated user."""

        params = {"method": "profile.get", "format": "json"}
        response = self.session.get(self.api_url, params=params)

        return self.valid_response(response)

    def profile_get_auth(self, user_id):
        """Returns the authentication information for a nominated user.

        :param user_id: The user_id specified in profile.create.
        :type user_id: str
        """

        params = {"method": "profile.get_auth", "format": "json", "user_id": user_id}

        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)
