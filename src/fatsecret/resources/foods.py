"""Foods resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

from ._generated.foods import FoodsResource as _GeneratedFoodsResource


class FoodsResource(_GeneratedFoodsResource):
    """Generated Foods resource plus a small set of hand-tuned overrides.

    Hand overrides (Phase 3 follow-up candidates):

      * ``get_v2`` — legacy method that bypasses ``_call`` and goes directly
        through ``session.get`` + ``valid_response``. Not OAS-derivable;
        retained verbatim from Phase 1.5.
    """

    def get_v2(self, food_id, region=None, language=None):
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
        return self._client.valid_response(response)


__all__ = ["FoodsResource"]
