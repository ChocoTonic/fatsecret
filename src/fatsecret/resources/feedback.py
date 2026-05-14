"""Feedback resource - generated. Override hand-tunings go below the import."""

from __future__ import annotations

from typing import Optional

from ._generated.feedback import FeedbackResource as _GeneratedFeedbackResource


class FeedbackResource(_GeneratedFeedbackResource):
    """Generated Feedback resource plus body-shape hand-overrides.

    Hand overrides:

      * ``submit_v1`` is overridden to fold ``returned_food_id`` and
        ``returned_serving_id`` into a nested ``returned_food`` object on the
        request body, matching the upstream wire format.  Codegen has no way
        to derive this grouping from the flat raw-YAML parameter list.
    """

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


__all__ = ["FeedbackResource"]
