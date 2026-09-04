"""HTTP facade authentication and idempotency tests."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
import yaml

from fatsecret import WebDiaryEntry, WebDiaryMeal, WebNutrition, WebRecipeDetail
from fatsecret.web.facade import MemberWebFacadeSettings, create_app


def _recipe(recipe_id: int = 42) -> WebRecipeDetail:
    return WebRecipeDetail(
        recipe_id=recipe_id,
        title="Bean Stew",
        description="Description",
        status="Pending",
        nutrition_per_serving=WebNutrition(calories=Decimal("100")),
        preview_url="https://example.test/recipe",
        edit_url="https://example.test/edit",
        servings=Decimal("4"),
        prep_minutes=5,
        cook_minutes=10,
        meal_types=[],
        directions=["Cook."],
        sharing=False,
        ingredients=[],
    )


class FakeClient:
    create_calls = 0
    diary_create_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def list_recipes(self):
        return []

    def create_recipe(self, recipe):
        type(self).create_calls += 1
        result = _recipe()
        return result.model_copy(update=recipe.model_dump())

    def get_recipe(self, recipe_id):
        return deepcopy(_recipe(recipe_id))

    def add_diary_entry(self, entry):
        type(self).diary_create_calls += 1
        return WebDiaryEntry(
            entry_id=501,
            item_id=entry.item_id,
            entry_name=entry.entry_name,
            amount=entry.amount,
            portion_id=0,
            portion_name="serving",
            meal=entry.meal,
            date=entry.date,
            edit_url="https://example.test/diary/501",
        )


def test_facade_requires_bearer_token(tmp_path):
    app = create_app(
        client_factory=FakeClient,
        bearer_token="test-token",
        database_path=tmp_path / "facade.sqlite3",
    )
    response = TestClient(app).get("/v1/member/recipes")

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "invalid_bearer_token"


def test_facade_replays_idempotent_recipe_create(tmp_path):
    FakeClient.create_calls = 0
    app = create_app(
        client_factory=FakeClient,
        bearer_token="test-token",
        database_path=tmp_path / "facade.sqlite3",
    )
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer test-token",
        "Idempotency-Key": "create-key-123",
    }
    body = {
        "title": "Bean Stew",
        "description": "Description",
        "servings": "4",
        "prep_minutes": 5,
        "cook_minutes": 10,
        "meal_types": [],
        "directions": ["Cook."],
    }

    first = client.post("/v1/member/recipes", headers=headers, json=body)
    second = client.post("/v1/member/recipes", headers=headers, json=body)

    assert first.status_code == 201
    assert first.headers["location"] == "/v1/member/recipes/42"
    assert second.status_code == 201
    assert second.headers["idempotent-replayed"] == "true"
    assert FakeClient.create_calls == 1


def test_facade_replays_idempotent_member_diary_create(tmp_path):
    FakeClient.diary_create_calls = 0
    app = create_app(
        client_factory=FakeClient,
        bearer_token="test-token",
        database_path=tmp_path / "facade.sqlite3",
    )
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer test-token",
        "Idempotency-Key": "diary-key-123",
    }
    body = {
        "item_id": 42,
        "entry_name": "Bean Stew",
        "amount": "10",
        "meal": WebDiaryMeal.DINNER.value,
        "date": 20699,
    }

    first = client.post("/v1/member/diary/entries", headers=headers, json=body)
    second = client.post("/v1/member/diary/entries", headers=headers, json=body)

    assert first.status_code == 201
    assert first.headers["location"] == "/v1/member/diary/entries/501?date=20699"
    assert second.headers["idempotent-replayed"] == "true"
    assert FakeClient.diary_create_calls == 1


def test_facade_routes_cover_every_manual_contract_operation(tmp_path):
    app = create_app(
        client_factory=FakeClient,
        bearer_token="test-token",
        database_path=tmp_path / "facade.sqlite3",
    )
    spec_path = (
        Path(__file__).resolve().parents[2] / "docs/api-spec/member-web.openapi.yaml"
    )
    spec = yaml.safe_load(spec_path.read_text())
    implemented = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    for path, path_item in spec["paths"].items():
        methods = {"get", "post", "put", "delete", "patch"} & path_item.keys()
        for method in methods:
            assert (method.upper(), f"/v1{path}") in implemented


def test_facade_settings_load_operational_configuration_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("FATSECRET_FACADE_TOKEN", "token")
    monkeypatch.setenv("FATSECRET_USERNAME", "member")
    monkeypatch.setenv("FATSECRET_PASSWORD", "secret")
    monkeypatch.setenv("FATSECRET_FACADE_DB", str(tmp_path / "state.sqlite3"))
    monkeypatch.setenv("FATSECRET_WEB_TIMEOUT", "12.5")
    monkeypatch.setenv("FATSECRET_WEB_RETRIES", "false")
    monkeypatch.setenv("FATSECRET_WEB_WAIT_ON_RATE_LIMIT", "false")
    monkeypatch.setenv("FATSECRET_FACADE_DEFAULT_RETRY_AFTER", "45")
    monkeypatch.setenv("FATSECRET_FACADE_MUTATION_DELAY_SECONDS", "0.25")
    monkeypatch.setenv("FATSECRET_FACADE_HOST", "0.0.0.0")
    monkeypatch.setenv("FATSECRET_FACADE_PORT", "9000")

    settings = MemberWebFacadeSettings.from_env()

    assert settings.client_timeout == 12.5
    assert settings.client_retries is False
    assert settings.wait_on_rate_limit is False
    assert settings.default_retry_after == 45
    assert settings.mutation_delay_seconds == 0.25
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.database_path == tmp_path / "state.sqlite3"
    assert "bearer_token='token'" not in repr(settings)
    assert "password='secret'" not in repr(settings)
    assert repr(settings).count("SecretStr('**********')") == 2


def test_facade_settings_reject_invalid_boolean(monkeypatch):
    monkeypatch.setenv("FATSECRET_FACADE_TOKEN", "token")
    monkeypatch.setenv("FATSECRET_WEB_RETRIES", "sometimes")

    with pytest.raises(ValueError, match="FATSECRET_WEB_RETRIES"):
        MemberWebFacadeSettings.from_env()
