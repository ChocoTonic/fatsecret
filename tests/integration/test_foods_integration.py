import pytest


@pytest.mark.integration
def test_food_get_basic(fatsecret_client):
    """Fetch a known food and verify essential fields."""
    food_id = "4380"
    result = fatsecret_client.food_get(food_id)

    assert isinstance(result, dict)
    assert result["food_id"] == food_id
    assert "food_name" in result
    assert "servings" in result


@pytest.mark.integration
def test_foods_search_basic(fatsecret_client):
    """Ensure searching returns a list of foods."""
    results = fatsecret_client.foods_search("banana")
    assert isinstance(results, list)
    assert any("banana" in f["food_name"].lower() for f in results)
