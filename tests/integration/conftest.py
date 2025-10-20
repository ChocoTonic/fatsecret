import os

import pytest
from dotenv import load_dotenv

from fatsecret.auth import fatsecret_authenticate


@pytest.fixture(scope="session")
def fatsecret_client():
    """Fixture to initialize authenticated Fatsecret client for integration tests."""

    if not os.getenv("GITHUB_ACTIONS"):
        load_dotenv()

    consumer_key = os.getenv("FATSECRET_CONSUMER_KEY")
    consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET")
    username = os.getenv("FATSECRET_USERNAME")
    password = os.getenv("FATSECRET_PASSWORD")

    if not consumer_key or not consumer_secret or not username or not password:
        pytest.fail("❌ Missing Fatsecret credentials in environment variables")

    fs = fatsecret_authenticate(username, password, consumer_key, consumer_secret)
    yield fs
    fs.close()
