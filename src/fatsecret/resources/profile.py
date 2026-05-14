"""Profile Auth resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

from typing import Any, Optional

from ._generated.profile import ProfileResource as _GeneratedProfileResource


class ProfileResource(_GeneratedProfileResource):
    """Generated Profile Auth resource plus tuple-coercion hand-overrides.

    Hand overrides:

      * ``create_v1`` / ``get_auth_v1`` — when the unwrapped ``profile`` dict
        carries ``auth_token`` we collapse the response into the
        ``(auth_token, auth_secret)`` 2-tuple expected by callers. The
        ``profile.get_auth`` endpoint is documented this way; ``profile.create``
        also returns the credentials when ``user_id`` was supplied.
    """

    def create_v1(self, user_id: Optional[str] = None) -> Any:
        params: dict = {"method": "profile.create"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._client._call(params, method="POST")
        profile = self._client._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile

    def get_auth_v1(self, user_id: Optional[str] = None) -> Any:
        params: dict = {"method": "profile.get_auth"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._client._call(params)
        profile = self._client._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile


__all__ = ["ProfileResource"]
