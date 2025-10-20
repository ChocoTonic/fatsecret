import os

import pytest
from dotenv import load_dotenv

from fatsecret import Fatsecret


@pytest.fixture(scope="module")
def fatsecret_client():
    """Fixture to initialize Fatsecret client for integration tests."""

    if not os.getenv("GITHUB_ACTIONS"):
        load_dotenv()

    consumer_key = os.getenv("FATSECRET_CONSUMER_KEY")
    consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET")

    if not consumer_key or not consumer_secret:
        pytest.skip("❌ Missing Fatsecret credentials in environment variables")

    fs = Fatsecret(consumer_key, consumer_secret)
    yield fs
    fs.close()
