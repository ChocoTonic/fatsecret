"""End-to-end smoke example for the fatsecret wrapper.

Reads credentials from `.env` at the repo root (gitignored). Runs both an
unauthenticated public-data flow and an authenticated 3-legged OAuth flow
against the live FatSecret API to confirm the wrapper actually works.

Run with::

    uv run python examples/main.py
    # or
    make example

Expected env vars (.env at repo root):

    FATSECRET_CONSUMER_KEY=...        # required
    FATSECRET_CONSUMER_SECRET=...     # required
    FATSECRET_USERNAME=...            # optional, enables OAuth section
    FATSECRET_PASSWORD=...            # optional, enables OAuth section
    FATSECRET_ACCESS_TOKEN=...        # optional, reuses saved session
    FATSECRET_ACCESS_SECRET=...       # optional, reuses saved session
"""

from __future__ import annotations

import os
import sys
import warnings
from pprint import pprint
from typing import Optional

from dotenv import load_dotenv

from fatsecret import Fatsecret


def heading(text: str) -> None:
    """Render a section divider."""
    bar = "=" * len(text)
    print(f"\n{bar}\n{text}\n{bar}")


def run_public_demo(fs: Fatsecret) -> None:
    """Exercise unauthenticated endpoints via the v2 namespaced surface."""
    heading("Public (unauthenticated) — namespaced surface")

    print("\nfs.foods.search_v1('Tacos') -> first 3 results")
    foods = fs.foods.search_v1("Tacos")
    pprint(foods[:3])

    print("\nfs.foods.get_v1(food_id='1345')")
    food = fs.foods.get_v1(food_id="1345")
    pprint(food)

    print("\nfs.recipes.search_v1('Tomato Soup') -> first 3 results")
    recipes = fs.recipes.search_v1("Tomato Soup")
    pprint(recipes[:3])

    print("\nfs.recipes.get_v1(recipe_id='88339')")
    recipe = fs.recipes.get_v1(recipe_id="88339")
    pprint(recipe)


def authenticate_from_env(
    consumer_key: str,
    consumer_secret: str,
    username: Optional[str],
    password: Optional[str],
    access_token: Optional[str],
    access_secret: Optional[str],
) -> Optional[Fatsecret]:
    """Return an authenticated Fatsecret instance, or None.

    Prefers saved access tokens; falls back to the HTML-form login flow
    if username/password are present.
    """
    if access_token and access_secret:
        print("\nUsing saved FATSECRET_ACCESS_TOKEN / FATSECRET_ACCESS_SECRET.")
        return Fatsecret(
            consumer_key,
            consumer_secret,
            session_token=(access_token, access_secret),
        )

    if username and password:
        print(
            "\nAuthenticating via FATSECRET_USERNAME / FATSECRET_PASSWORD (HTML scrape)."
        )
        # `Fatsecret.fatsecret_authenticate` is a helper defined on the class
        # (no `self`) that drives the 3-legged OAuth flow programmatically.
        return Fatsecret.fatsecret_authenticate(
            username, password, consumer_key, consumer_secret
        )

    return None


def run_authenticated_demo(fs_auth: Fatsecret) -> None:
    """Exercise profile-scoped endpoints via the v2 namespaced surface."""
    heading("Authenticated (3-legged OAuth) — namespaced surface")

    print("\nfs.recipes.search_v1('Enchiladas') -> first 3 results")
    recipes = fs_auth.recipes.search_v1("Enchiladas")
    pprint(recipes[:3])

    print("\nfs.profile.get_v1()")
    profile = fs_auth.profile.get_v1()
    pprint(profile)

    print("\nfs.profile_foods.get_most_eaten_v1() — first 3")
    most_eaten = fs_auth.profile_foods.get_most_eaten_v1()
    pprint(most_eaten[:3] if isinstance(most_eaten, list) else most_eaten)

    def _tail(s: str) -> str:
        return f"****{s[-4:]}" if s and len(s) > 4 else "****"

    masked = (_tail(fs_auth.access_token), _tail(fs_auth.access_token_secret))
    print(
        "\nSave these as FATSECRET_ACCESS_TOKEN / FATSECRET_ACCESS_SECRET to skip\n"
        f"the HTML-scrape next time (printed masked, look in fs_auth.access_token /\n"
        f"fs_auth.access_token_secret for the full values):\n  {masked}"
    )


def main() -> int:
    load_dotenv()

    consumer_key = os.getenv("FATSECRET_CONSUMER_KEY")
    consumer_secret = os.getenv("FATSECRET_CONSUMER_SECRET")
    username = os.getenv("FATSECRET_USERNAME")
    password = os.getenv("FATSECRET_PASSWORD")
    access_token = os.getenv("FATSECRET_ACCESS_TOKEN")
    access_secret = os.getenv("FATSECRET_ACCESS_SECRET")

    if not consumer_key or not consumer_secret:
        print(
            "Missing FATSECRET_CONSUMER_KEY / FATSECRET_CONSUMER_SECRET.\n"
            "Create a .env at the repo root with at least:\n"
            "  FATSECRET_CONSUMER_KEY=...\n"
            "  FATSECRET_CONSUMER_SECRET=...",
            file=sys.stderr,
        )
        return 1

    # Show our own DeprecationWarnings so a maintainer running this gets a
    # nudge if they accidentally call a flat alias.
    warnings.filterwarnings("default", category=DeprecationWarning, module="fatsecret")

    fs = Fatsecret(consumer_key, consumer_secret)
    run_public_demo(fs)

    fs_auth = authenticate_from_env(
        consumer_key, consumer_secret, username, password, access_token, access_secret
    )
    if fs_auth is None:
        heading("Authenticated demo SKIPPED")
        print(
            "No usable credentials.\n"
            "Set FATSECRET_USERNAME + FATSECRET_PASSWORD or\n"
            "FATSECRET_ACCESS_TOKEN + FATSECRET_ACCESS_SECRET in .env."
        )
        return 0

    run_authenticated_demo(fs_auth)
    return 0


if __name__ == "__main__":
    sys.exit(main())
