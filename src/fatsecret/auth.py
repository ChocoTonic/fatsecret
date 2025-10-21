import os
from typing import Optional
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from fatsecret import Fatsecret


def fatsecret_authenticate(
    username: Optional[str],
    password: Optional[str],
    consumer_key: str,
    consumer_secret: str,
) -> Optional[Fatsecret]:
    """Authenticate a user programmatically using credentials and return an authorized Fatsecret instance.

    Behavior:
    - If FATSECRET_ACCESS_TOKEN and FATSECRET_ACCESS_SECRET env vars are present,
      use them to create an authenticated client and return immediately.
    - Otherwise attempt the HTML form emulation flow used previously.
    - On any failure the function returns None (preserving existing unit-test
      semantics). The integration test conftest provides a fallback consumer-only
      client when None is returned.

    Note:
    This uses HTML form emulation against FatSecret's login flow and may break
    if the website changes. It is provided for convenience and developer
    testing, not production OAuth flows.
    """
    # Allow callers to provide an already-authorized token pair via env vars
    access_token = os.getenv("FATSECRET_ACCESS_TOKEN")
    access_secret = os.getenv("FATSECRET_ACCESS_SECRET")
    if access_token and access_secret:
        return Fatsecret(
            consumer_key, consumer_secret, session_token=(access_token, access_secret)
        )

    # If username/password are not provided, do not attempt the HTML form
    # authentication flow — return None so callers may choose to fall back to a
    # consumer-only client.
    if not username or not password:
        return None

    try:
        session = requests.Session()
        fatsecret_client = Fatsecret(consumer_key, consumer_secret)
        # Build the authorize.aspx login URL robustly.
        raw_authorize = fatsecret_client.get_authorize_url()
        parsed = urlparse(raw_authorize)
        # If the path ends with 'authorize' replace it with 'authorize.aspx'
        if parsed.path.endswith("/authorize") or parsed.path.endswith("authorize"):
            new_path = parsed.path.rstrip("/")
            if new_path.endswith("authorize"):
                new_path = new_path[: -len("authorize")] + "authorize.aspx"
            authorize_url = urlunparse(parsed._replace(path=new_path))
        else:
            # Fallback to the original replace used in tests/mocks.
            authorize_url = raw_authorize.replace("authorize", "authorize.aspx")

        # Fetch viewstate and generator dynamically
        login_page_response = session.get(url=authorize_url)
        login_page_soup = BeautifulSoup(login_page_response.text, "lxml")
        viewstate_input = login_page_soup.find("input", {"name": "__VIEWSTATE"})
        viewstate_generator_input = login_page_soup.find(
            "input", {"name": "__VIEWSTATEGENERATOR"}
        )
        if viewstate_input is None or viewstate_generator_input is None:
            raise RuntimeError("Missing __VIEWSTATE inputs on login page")

        viewstate_value = viewstate_input["value"]
        viewstate_generator_value = viewstate_generator_input["value"]

        payload = {
            "__VIEWSTATE": viewstate_value,
            "__VIEWSTATEGENERATOR": viewstate_generator_value,
            "Name": username,
            "Password": password,
            "Login.x": 0,
            "Login.y": 0,
        }

        pin_response = session.post(url=authorize_url, data=payload)
        pin_soup = BeautifulSoup(pin_response.content, "lxml")
        verifier_tag = pin_soup.find("b")
        if not verifier_tag:
            raise RuntimeError("Failed to find PIN in response. Login may have failed.")
        verifier_pin = verifier_tag.text.strip()
        print(f"Obtained verifier PIN. {len(verifier_pin) = }")
        fatsecret_client.authenticate(verifier_pin)
        print("Authentication successful.")
        return fatsecret_client
    except Exception as error:
        message = f"Failed to authenticate:\n{error}"
        print(message)
        return None
