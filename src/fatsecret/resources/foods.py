"""Foods resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

from typing import Optional

from ..models._generated.foods import Food
from ._generated.foods import FoodsResource as _GeneratedFoodsResource


class FoodsResource(_GeneratedFoodsResource):
    """Generated Foods resource plus a small set of hand-tuned overrides.

    Hand overrides (Phase 3 follow-up candidates):

      * ``get_v2`` — legacy method that bypasses ``_call`` and goes directly
        through ``session.get`` + ``valid_response``. Not OAS-derivable;
        retained verbatim from Phase 1.5 with Phase 2 typed-model wrapping.
    """

    def get_v2(self, food_id, region=None, language=None) -> Optional[Food]:
        """Returns detailed nutritional information for the specified food.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """
        params = {"method": "food.get.v2", "food_id": food_id, "format": "json"}
        if region:
            params["region"] = region
        if language:
            params["language"] = language
        response = self._client.session.get(self._client.api_url, params=params)
        # ``valid_response`` for the ``food`` key returns the unwrapped
        # ``response.json()["food"]`` dict directly; wrap it in our model.
        raw = self._client.valid_response(response)
        if raw is None:
            return None
        return Food.model_validate(raw)


__all__ = ["FoodsResource"]
