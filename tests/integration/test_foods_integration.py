from pprint import pprint

import pytest


@pytest.mark.integration
def test_food_get_basic(fatsecret_client):
    """Test a simple public call to the Fatsecret API."""
    food_id = "4380"

    result = fatsecret_client.food_get(food_id)
    pprint("result")
    pprint(result)

    # Basic sanity checks
    assert isinstance(result, dict)
    assert "food_id" in result
    assert result["food_id"] == food_id
    assert "food_name" in result
