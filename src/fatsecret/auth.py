import requests
from bs4 import BeautifulSoup

from fatsecret import Fatsecret


def fatsecret_authenticate(
    username: str, password: str, consumer_key: str, consumer_secret: str
) -> Fatsecret:
    """Authenticate a user programmatically using credentials and return an authorized Fatsecret instance.

    Note:
    This uses HTML form emulation against FatSecret's login flow and may break if the website changes.
    It is provided for convenience and developer testing, not production OAuth flows.
    """
    try:
        session = requests.Session()
        fatsecret_client = Fatsecret(consumer_key, consumer_secret)
        authorize_url = fatsecret_client.get_authorize_url().replace(
            "authorize", "authorize.aspx"
        )

        # Fetch viewstate and generator dynamically
        login_page_response = session.get(url=authorize_url)
        login_page_soup = BeautifulSoup(login_page_response.text, "lxml")
        viewstate_value = login_page_soup.find("input", {"name": "__VIEWSTATE"})[
            "value"
        ]
        viewstate_generator_value = login_page_soup.find(
            "input", {"name": "__VIEWSTATEGENERATOR"}
        )["value"]

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
        print(f"Obtained verifier PIN: {verifier_pin}")
        fatsecret_client.authenticate(verifier_pin)
        print(f"Authenticated as {username}!")
        return fatsecret_client
    except Exception as error:
        message = f"Failed to authenticate:\n{error}"
        print(message)
        return None
