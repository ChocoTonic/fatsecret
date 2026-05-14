"""Native APIs resource - generated. Override hand-tunings go below the import.

The Native APIs (NLP, image recognition) use a non-standard ``_call`` shape:
``params={"format": "json"}`` as a kwarg, request body as ``json_body``, and a
post-unwrap ``or []`` collapse when the upstream response is empty.  Codegen
emits the canonical method-style shape; we re-implement the methods here to
preserve the test-asserted wire format.
"""

from __future__ import annotations

from typing import Optional

from ._generated.native import NativeResource as _GeneratedNativeResource


class NativeResource(_GeneratedNativeResource):
    """Generated Native APIs resource plus body-and-params hand-overrides."""

    def image_recognition_v1(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        return self._image_recognition_impl(
            "https://platform.fatsecret.com/rest/image-recognition/v1",
            image_b64,
            include_food_data,
            eaten_foods,
            region,
            language,
        )

    def image_recognition_v2(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        return self._image_recognition_impl(
            "https://platform.fatsecret.com/rest/image-recognition/v2",
            image_b64,
            include_food_data,
            eaten_foods,
            region,
            language,
        )

    def natural_language_processing_v1(
        self,
        user_input: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
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

    def _image_recognition_impl(
        self,
        url: str,
        image_b64: str,
        include_food_data,
        eaten_foods,
        region,
        language,
    ):
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
            url=url,
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._client._unwrap(payload, "food_response", list_key=None) or []
        return payload


__all__ = ["NativeResource"]
