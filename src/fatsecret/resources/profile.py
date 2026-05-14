"""Resource methods for the OAS ``Profile`` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class ProfileResource(BaseResource):
    """Resource methods for the OAS `Profile` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def create_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.profile_create_v1`."""
        return self._client.profile_create_v1(*args, **kwargs)

    def get_auth_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.profile_get_auth_v1`."""
        return self._client.profile_get_auth_v1(*args, **kwargs)

    def get_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.profile_get_v1`."""
        return self._client.profile_get_v1(*args, **kwargs)
