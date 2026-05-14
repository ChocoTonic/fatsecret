"""Resource methods for the OAS ``Profile`` tag."""

from __future__ import annotations

from typing import Any, Optional

from ._base import BaseResource


class ProfileResource(BaseResource):
    """Resource methods for the OAS `Profile` tag."""

    def create_v1(self, user_id: Optional[str] = None) -> Any:
        """profile.create v1. Returns (auth_token, auth_secret) when user_id is supplied."""
        params: dict = {"method": "profile.create"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._client._call(params, method="POST")
        profile = self._client._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile

    def get_v1(self) -> dict:
        """profile.get v1. Returns the user's profile dict."""
        payload = self._client._call({"method": "profile.get"})
        return self._client._unwrap(payload, "profile")

    def get_auth_v1(self, user_id: Optional[str] = None) -> Any:
        """profile.get_auth v1. Returns (auth_token, auth_secret)."""
        params: dict = {"method": "profile.get_auth"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._client._call(params)
        profile = self._client._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile
