"""Resource wrapper for the OAS `Feedback` tag."""

from __future__ import annotations

from typing import Optional

from ._base import BaseResource


class FeedbackResource(BaseResource):
    """Resource methods for the OAS `Feedback` tag."""

    def submit_v1(
        self,
        issue_type_id: int,
        external_id: str,
        barcode: Optional[int] = None,
        issue_type: Optional[str] = None,
        notes: Optional[str] = None,
        returned_food_id: Optional[int] = None,
        returned_serving_id: Optional[int] = None,
        image_file_extension: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """feedback v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `feedback`. issue_type_id codes:
        1=Wrong Name/Brand, 2=Wrong Nutrition, 3=Missing Serving Size,
        4=Barcode not found, 99=Other.
        """
        body: dict = {"issue_type_id": issue_type_id, "external_id": external_id}
        if barcode is not None:
            body["barcode"] = barcode
        if issue_type is not None:
            body["issue_type"] = issue_type
        if notes is not None:
            body["notes"] = notes
        if returned_food_id is not None or returned_serving_id is not None:
            returned_food: dict = {}
            if returned_food_id is not None:
                returned_food["food_id"] = returned_food_id
            if returned_serving_id is not None:
                returned_food["serving_id"] = returned_serving_id
            body["returned_food"] = returned_food
        if image_file_extension is not None:
            body["image_file_extension"] = image_file_extension
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._client._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/feedback/v1",
            method="POST",
            json_body=body,
        )
        return payload
