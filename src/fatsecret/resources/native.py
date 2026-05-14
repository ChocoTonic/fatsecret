"""Resource wrapper for the OAS ``Native`` tag."""

from __future__ import annotations

from typing import Optional

from ._base import BaseResource


class NativeResource(BaseResource):
    """Resource methods for the OAS `Native` tag.

    Phase 1: pure-delegation over the flat ``natural_language_processing_*``
    and ``image_recognition_*`` methods on :class:`Fatsecret`. Future phases
    swap delegation for OAS-codegen'd implementations.
    """

    def image_recognition_v1(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """image.recognition v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `image-recognition`. image_b64 max ~999,982 chars.
        """
        body: dict = {"image_b64": image_b64}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._client._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/image-recognition/v1",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._client._unwrap(payload, "food_response", list_key=None) or []
        return payload

    def image_recognition_v2(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """image.recognition v2. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `image-recognition`. Faster inference, better
        handling of generic/restaurant/mixed foods.
        """
        body: dict = {"image_b64": image_b64}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._client._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/image-recognition/v2",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._client._unwrap(payload, "food_response", list_key=None) or []
        return payload

    def natural_language_processing_v1(
        self,
        user_input: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """natural.language.processing v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `nlp`. user_input limited to 1000 chars.
        """
        body: dict = {"user_input": user_input}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._client._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/natural-language-processing/v1",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._client._unwrap(payload, "food_response", list_key=None) or []
        return payload
