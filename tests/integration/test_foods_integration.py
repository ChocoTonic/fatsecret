import pytest


@pytest.mark.integration
def test_food_get_basic(fatsecret_client):
    """Fetch a known food and verify essential fields."""
    food_id = "4380"
    result = fatsecret_client.foods.get_v1(food_id=food_id)

    assert result is not None
    assert str(result.food_id) == food_id
    assert result.food_name is not None
    assert result.servings is not None


@pytest.mark.integration
def test_foods_search_basic(fatsecret_client):
    """Ensure searching returns a list of foods."""
    results = fatsecret_client.foods.search_v1("banana")
    assert isinstance(results, list)
    assert any("banana" in f.food_name.lower() for f in results)


@pytest.mark.integration
def test_food_get_v2_basic(fatsecret_client):
    """Fetch a known food using v2 and verify essential fields."""
    food_id = "4380"
    result = fatsecret_client.foods.get_v2(food_id=food_id)
    assert result is not None
    assert str(result.food_id) == food_id
    assert result.food_name is not None
    assert result.servings is not None


@pytest.mark.integration
def test_food_get_v2_with_region(fatsecret_client):
    """Test foods.get_v2 with region parameter."""
    food_id = "4380"
    result = fatsecret_client.foods.get_v2(food_id=food_id, region="US")
    assert result is not None
    assert str(result.food_id) == food_id
    assert result.food_name is not None
    assert result.servings is not None


@pytest.mark.integration
def test_food_get_v2_with_language(fatsecret_client):
    """Test foods.get_v2 with language parameter."""
    food_id = "4380"
    result = fatsecret_client.foods.get_v2(food_id=food_id, language="en")
    assert result is not None
    assert str(result.food_id) == food_id
    assert result.food_name is not None
    assert result.servings is not None
