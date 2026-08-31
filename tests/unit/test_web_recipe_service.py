"""Durable recipe copy orchestration tests."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from fatsecret import (
    FatsecretWebIdempotencyConflictError,
    FatsecretWebRateLimitError,
    WebIngredientWrite,
    WebNutrition,
    WebRecipeDetail,
    WebRecipeIngredient,
    WebRecipeSummary,
    WebRecipeSummaryNutrition,
)
from fatsecret.web.service import (
    IdempotencyStore,
    RecipeCopyService,
    RecipeOperationStore,
)


def _ingredient(entry_id: int, food_id: int, amount: str, portion_id: int):
    return WebRecipeIngredient(
        entry_id=entry_id,
        food_id=food_id,
        name=f"Food {food_id}",
        amount=Decimal(amount),
        portion_id=portion_id,
        portion_name="g",
        display_text=f"{amount} g food {food_id}",
        nutrition_total=WebNutrition(),
    )


def _detail(recipe_id: int, title: str, ingredients):
    return WebRecipeDetail(
        recipe_id=recipe_id,
        title=title,
        description="Description",
        status="Pending",
        nutrition_per_serving=WebNutrition(calories=Decimal("100")),
        preview_url=f"https://example.test/recipes/{recipe_id}",
        edit_url=f"https://example.test/edit/{recipe_id}",
        date_published=date(2026, 8, 26),
        servings=Decimal("4"),
        prep_minutes=5,
        cook_minutes=10,
        meal_types=[],
        directions=["Cook."],
        sharing=False,
        ingredients=ingredients,
    )


class FakeClient:
    rate_limit_food_id = None
    rate_limited = False

    def __init__(self):
        self.source = _detail(
            10,
            "Source",
            [_ingredient(101, 201, "15", 301), _ingredient(102, 202, "20", 302)],
        )
        self.target = None
        self.next_entry_id = 1000

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def list_recipes(self):
        details = [self.source] + ([self.target] if self.target else [])
        return [
            WebRecipeSummary(
                recipe_id=item.recipe_id,
                title=item.title,
                description=item.description,
                status=item.status,
                nutrition=WebRecipeSummaryNutrition(calories=Decimal("100")),
                preview_url=item.preview_url,
                edit_url=item.edit_url,
            )
            for item in details
        ]

    def get_recipe(self, recipe_id):
        if recipe_id == self.source.recipe_id:
            return deepcopy(self.source)
        if self.target and recipe_id == self.target.recipe_id:
            return deepcopy(self.target)
        raise AssertionError(recipe_id)

    def create_recipe(self, recipe):
        self.target = _detail(20, recipe.title, [])
        return deepcopy(self.target)

    def add_recipe_ingredient(self, recipe_id: int, ingredient: WebIngredientWrite):
        assert recipe_id == 20
        if ingredient.food_id == self.rate_limit_food_id and not self.rate_limited:
            self.rate_limited = True
            raise FatsecretWebRateLimitError("slow down", retry_after=0)
        added = _ingredient(
            self.next_entry_id,
            ingredient.food_id,
            str(ingredient.amount),
            ingredient.portion_id,
        )
        self.next_entry_id += 1
        self.target.ingredients.append(added)
        return deepcopy(added)


def test_copy_completes_and_replays_idempotency_key(tmp_path):
    client = FakeClient()
    service = RecipeCopyService(
        lambda: client,
        RecipeOperationStore(tmp_path / "operations.sqlite3"),
        mutation_delay_seconds=0,
    )
    operation = service.start_copy(10, "Source - copy", "copy-key-123")

    completed = service.run_copy(operation.operation_id)
    replayed = service.start_copy(10, "Source - copy", "copy-key-123")

    assert completed.status == "completed"
    assert completed.target_recipe_id == 20
    assert completed.completed_ingredient_count == 2
    assert [item.food_id for item in completed.result.ingredients] == [201, 202]
    assert replayed.operation_id == operation.operation_id


def test_copy_pauses_on_rate_limit_and_reconciles_before_resume(tmp_path):
    client = FakeClient()
    client.rate_limit_food_id = 202
    service = RecipeCopyService(
        lambda: client,
        RecipeOperationStore(tmp_path / "operations.sqlite3"),
        default_retry_after=0,
        mutation_delay_seconds=0,
    )
    operation = service.start_copy(10, "Source - copy", "copy-key-456")

    waiting = service.run_copy(operation.operation_id)
    completed = service.run_copy(operation.operation_id)

    assert waiting.status == "waiting"
    assert waiting.completed_ingredient_count == 1
    assert completed.status == "completed"
    assert [item.food_id for item in client.target.ingredients] == [201, 202]


def test_copy_rejects_idempotency_key_reuse_with_new_payload(tmp_path):
    service = RecipeCopyService(
        FakeClient, RecipeOperationStore(tmp_path / "operations.sqlite3")
    )
    service.start_copy(10, "First title", "copy-key-789")

    with pytest.raises(FatsecretWebIdempotencyConflictError):
        service.start_copy(10, "Different title", "copy-key-789")


def test_pending_synchronous_write_becomes_unknown_after_restart(tmp_path):
    path = tmp_path / "operations.sqlite3"
    store = IdempotencyStore(path)
    assert store.begin("create", "create-key-123", {"title": "one"}) is None

    restarted = IdempotencyStore(path)
    recovered = restarted.begin("create", "create-key-123", {"title": "one"})

    assert recovered["state"] == "unknown"
    assert "restarted" in recovered["error"]
