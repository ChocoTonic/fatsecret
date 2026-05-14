"""Resource wrapper for the OAS ``Native`` tag."""

from __future__ import annotations

from typing import Any

from ._base import BaseResource


class NativeResource(BaseResource):
    """Resource methods for the OAS `Native` tag.

    Phase 1: pure-delegation over the flat ``natural_language_processing_*``
    and ``image_recognition_*`` methods on :class:`Fatsecret`. Future phases
    swap delegation for OAS-codegen'd implementations.
    """

    def image_recognition_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.image_recognition_v1`."""
        return self._client.image_recognition_v1(*args, **kwargs)

    def image_recognition_v2(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.image_recognition_v2`."""
        return self._client.image_recognition_v2(*args, **kwargs)

    def natural_language_processing_v1(self, *args: Any, **kwargs: Any) -> Any:
        """Delegate to :meth:`Fatsecret.natural_language_processing_v1`."""
        return self._client.natural_language_processing_v1(*args, **kwargs)
