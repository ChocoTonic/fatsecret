"""Resource wrapper for the OAS `Weight` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class WeightResource(BaseResource):
    """Resource methods for the OAS `Weight` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def get_month_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.weights_get_month_v1`."""
        return self._client.weights_get_month_v1(*args, **kwargs)

    def get_month_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.weights_get_month_v2`."""
        return self._client.weights_get_month_v2(*args, **kwargs)

    def update_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.weight_update_v1`."""
        return self._client.weight_update_v1(*args, **kwargs)
