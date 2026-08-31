"""Contract tests for the manually maintained member-web facade OAS."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from openapi_spec_validator import validate

SPEC_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "api-spec"
    / "member-web.openapi.yaml"
)
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options"}
REQUIRED_EXTENSIONS = {
    "x-fatsecret-interface": "member-website",
    "x-support-status": "unofficial",
    "x-upstream-stability": "unstable",
}


def _load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text())


def _operations(spec: dict):
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            if method in HTTP_METHODS:
                yield path, method, operation


def test_member_web_oas_is_valid_openapi_31():
    spec = _load_spec()

    validate(spec)
    assert re.fullmatch(r"\d+\.\d+\.\d+", spec["info"]["version"])
    assert spec["info"]["x-contract-status"] == "experimental"


def test_member_web_operations_have_unique_ids_and_ownership_metadata():
    operations = list(_operations(_load_spec()))
    operation_ids = [operation["operationId"] for _, _, operation in operations]

    assert len(operation_ids) == len(set(operation_ids))
    for path, method, operation in operations:
        for name, expected in REQUIRED_EXTENSIONS.items():
            assert operation.get(name) == expected, f"{method.upper()} {path}: {name}"
        assert "x-implementation-status" in operation
        assert "x-retry-policy" in operation


def test_every_mutation_requires_verification_and_declares_ambiguous_failure():
    for path, method, operation in _operations(_load_spec()):
        if method not in {"post", "put", "delete", "patch"}:
            continue
        assert operation.get("x-write-verification") == "required", (
            f"{method.upper()} {path}"
        )
        assert "504" in operation["responses"], f"{method.upper()} {path}"


def test_create_operations_require_idempotency_keys():
    spec = _load_spec()
    for path in [
        "/member/recipes",
        "/member/recipes/{recipe_id}/ingredients",
        "/member/recipes/{recipe_id}/copies",
    ]:
        operation = spec["paths"][path]["post"]
        assert operation["x-retry-policy"] == "idempotency-key-required"
        assert {"$ref": "#/components/parameters/IdempotencyKey"} in operation[
            "parameters"
        ]


def test_fatsecret_credentials_are_not_part_of_the_contract():
    serialized = SPEC_PATH.read_text().lower()
    forbidden = ["fatsecret_password", "fs_password", ".fsaspxauth"]

    assert not any(secret in serialized for secret in forbidden)


def test_portion_resolution_is_scoped_to_destination_recipe():
    paths = _load_spec()["paths"]

    assert "/member/recipes/{recipe_id}/foods/{food_id}/portions" in paths
    assert "/member/foods/{food_id}/portions" not in paths
