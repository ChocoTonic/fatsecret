"""Resource wrapper for the OAS `Feedback` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class FeedbackResource(BaseResource):
    """Resource methods for the OAS `Feedback` tag.

    Phase 1: pure-delegation over flat methods on :class:`Fatsecret`.
    """

    def submit_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.feedback_v1`."""
        return self._client.feedback_v1(*args, **kwargs)
