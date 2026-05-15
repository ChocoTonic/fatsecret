"""Tests for the codegen'd ``foods`` Pydantic models (Phase 1)."""

from __future__ import annotations

import hashlib
import subprocess
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from fatsecret.models import Food, Serving
from fatsecret.models._common import Ternary  # noqa: F401  (used in annotation tests)


REPO_ROOT = Path(__file__).resolve().parents[3]
GEN_FILE = REPO_ROOT / "src" / "fatsecret" / "models" / "_generated" / "foods.py"
OAS_SYNC_DIR = REPO_ROOT / "scripts" / "oas-sync"


def test_food_coerces_string_id_to_int() -> None:
    food = Food.model_validate(
        {"food_id": "36421", "food_name": "Banana", "food_type": "Generic", "food_url": "x"}
    )
    assert food.food_id == 36421
    assert isinstance(food.food_id, int)
    assert food.food_name == "Banana"
    assert food.food_type == "Generic"


def test_food_accepts_native_int_id() -> None:
    food = Food.model_validate(
        {"food_id": 36421, "food_name": "Banana", "food_type": "Generic", "food_url": "x"}
    )
    assert food.food_id == 36421


def test_food_preserves_unknown_fields() -> None:
    food = Food.model_validate(
        {
            "food_id": "1",
            "food_name": "X",
            "food_type": "Brand",
            "food_url": "u",
            "future_field": "x",
        }
    )
    # ``extra="allow"`` keeps the field accessible via attribute and dict.
    assert food.future_field == "x"  # type: ignore[attr-defined]
    assert food.model_dump()["future_field"] == "x"


def test_food_to_dict_serializes_decimals_as_strings() -> None:
    food = Food.model_validate(
        {
            "food_id": "1",
            "food_name": "X",
            "food_type": "Brand",
            "food_url": "u",
            "servings": {
                "serving": [
                    {
                        "serving_id": "1",
                        "serving_description": "1 unit",
                        "serving_url": "u",
                        "number_of_units": "1",
                        "measurement_description": "unit",
                        "is_default": True,
                        "calories": "100.5",
                        "carbohydrate": "20",
                        "protein": "1",
                        "fat": "0.5",
                    }
                ]
            },
        }
    )
    blob = food.to_dict()
    serving = blob["servings"]["serving"][0]
    assert serving["calories"] == "100.5"
    assert isinstance(serving["calories"], str)


def test_codegen_is_byte_deterministic() -> None:
    """Two consecutive ``emit-models foods`` runs must produce identical bytes."""

    def _md5() -> str:
        return hashlib.md5(GEN_FILE.read_bytes()).hexdigest()

    first = _md5()
    subprocess.run(
        ["uv", "run", "oas-sync", "emit-models", "foods"],
        cwd=OAS_SYNC_DIR,
        check=True,
        capture_output=True,
    )
    second = _md5()
    subprocess.run(
        ["uv", "run", "oas-sync", "emit-models", "foods"],
        cwd=OAS_SYNC_DIR,
        check=True,
        capture_output=True,
    )
    third = _md5()
    assert first == second == third


@pytest.mark.parametrize("value", [1, -1, 0, "True", "False", "Unknown"])
def test_ternary_accepts_documented_values(value: object) -> None:
    from fatsecret.models import Allergen

    a = Allergen.model_validate({"id": 1, "name": "Peanut", "value": value})
    assert a.value == value


def test_ternary_rejects_undocumented_value() -> None:
    from fatsecret.models import Allergen

    with pytest.raises(ValidationError):
        Allergen.model_validate({"id": 1, "name": "Peanut", "value": "Maybe"})


def test_serving_calories_typed_as_decimal() -> None:
    serving = Serving.model_validate(
        {
            "serving_id": "1",
            "serving_description": "1 unit",
            "serving_url": "u",
            "number_of_units": "1",
            "measurement_description": "unit",
            "is_default": True,
            "calories": "100.5",
            "carbohydrate": "20",
            "protein": "1",
            "fat": "0.5",
        }
    )
    assert serving.calories == Decimal("100.5")
    assert isinstance(serving.calories, Decimal)
