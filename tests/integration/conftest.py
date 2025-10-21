import json
import os

import pytest
import requests
from dotenv import load_dotenv

from fatsecret import Fatsecret
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

    if not consumer_key:
        pytest.fail("❌ Missing FATSECRET_CONSUMER_KEY in environment variables")
    if not consumer_secret:
        pytest.fail("❌ Missing FATSECRET_CONSUMER_SECRET in environment variables")
    if not username:
        pytest.fail("❌ Missing FATSECRET_USERNAME in environment variables")
    if not password:
        pytest.fail("❌ Missing FATSECRET_PASSWORD in environment variables")

    fs = fatsecret_authenticate(username, password, consumer_key, consumer_secret)
    if fs is None:
        # If programmatic login fails, fall back to a consumer-only signed
        # client so tests that do not require user-specific data can still run.
        print(
            "Failed to authenticate with username/password; using consumer-only client."
        )
        fs = Fatsecret(consumer_key, consumer_secret)

    yield fs
    # Be defensive in teardown: only call close if the client exists and
    # provides a close method.
    if fs and hasattr(fs, "close"):
        fs.close()


@pytest.fixture
def make_response():
    def _make_response(json_data):
        resp = requests.Response()
        resp.status_code = 200
        resp._content = json.dumps(json_data).encode("utf-8")
        return resp

    return _make_response
