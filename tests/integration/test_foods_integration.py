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


@pytest.mark.integration
def test_food_get_v2_basic(fatsecret_client):
    """Fetch a known food using v2 and verify essential fields."""
    food_id = "4380"
    result = fatsecret_client.food_get_v2(food_id)
    assert isinstance(result, dict)
    assert result["food_id"] == food_id
    assert "food_name" in result
    assert "servings" in result


@pytest.mark.integration
def test_food_get_v2_with_region(fatsecret_client):
    """Test food_get_v2 with region parameter."""
    food_id = "4380"
    # Use a valid region code, e.g., 'US'
    result = fatsecret_client.food_get_v2(food_id, region="US")
    assert isinstance(result, dict)
    assert result["food_id"] == food_id
    assert "food_name" in result
    assert "servings" in result


@pytest.mark.integration
def test_food_get_v2_with_language(fatsecret_client):
    """Test food_get_v2 with language parameter."""
    food_id = "4380"
    # Use a valid language code, e.g., 'en'
    result = fatsecret_client.food_get_v2(food_id, language="en")
    assert isinstance(result, dict)
    assert result["food_id"] == food_id
    assert "food_name" in result
    assert "servings" in result
