"""Tests for the unofficial authenticated member-recipe client."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock

import pytest

from fatsecret import (
    FatsecretWebAuthenticationError,
    FatsecretWebClient,
    FatsecretWebParseError,
)


def _response(text: str, url: str) -> Mock:
    response = Mock()
    response.text = text
    response.url = url
    response.raise_for_status.return_value = None
    return response


def _login_html() -> str:
    return """
    <html><body><form>
      <input type="hidden" name="__VIEWSTATE" value="state-value">
      <input type="hidden" name="__VIEWSTATEGENERATOR" value="generator-value">
    </form></body></html>
    """


def _cookbook_html(*, declared_count: int = 2) -> str:
    return f"""
    <html><body>
      <div>Hello member | Sign out</div>
      <div>you have submitted {declared_count} recipes</div>
      <table class="generic">
        <tr><td class="borderBottom">
          <h2 class="prominent">
            <a href="/recipes/rec-one/Default.aspx">First Recipe</a>
            <span class="smallText">(Pending)</span>
          </h2>
          <div class="smallText" style="font-weight:bold;margin-left:5px">
            cals: 123kcal | fat: 4.50g | carbs: 20.25g | prot: 7.00g
          </div>
          <table><tr><td><div class="greyText">"First description"</div></td></tr></table>
          <a href="/Diary.aspx?pa=mrece&amp;recipeid=101">edit recipe</a>
        </td></tr>
        <tr><td class="borderBottom">
          <h2 class="prominent">
            <a href="/recipes/rec-two/Default.aspx">Second Recipe</a>
            <span class="smallText">(Published)</span>
          </h2>
          <div class="smallText" style="font-weight:bold">
            cals: 1,234kcal | fat: 10.00g | carbs: 200.00g | prot: 30.50g
          </div>
          <table><tr><td><div class="greyText">"Second description"</div></td></tr></table>
          <a href="/Diary.aspx?pa=mrece&amp;recipeid=202">edit recipe</a>
        </td></tr>
      </table>
    </body></html>
    """


def test_parse_recipe_summaries_returns_typed_metadata():
    recipes = FatsecretWebClient._parse_recipe_summaries(_cookbook_html())

    assert [recipe.recipe_id for recipe in recipes] == [101, 202]
    assert recipes[0].title == "First Recipe"
    assert recipes[0].description == "First description"
    assert recipes[0].status == "Pending"
    assert recipes[0].nutrition.calories == Decimal("123")
    assert recipes[0].nutrition.fat_g == Decimal("4.50")
    assert recipes[0].nutrition.carbohydrate_g == Decimal("20.25")
    assert recipes[0].nutrition.protein_g == Decimal("7.00")
    assert recipes[0].preview_url.endswith("/recipes/rec-one/Default.aspx")
    assert recipes[0].edit_url.endswith("recipeid=101")
    assert recipes[1].nutrition.calories == Decimal("1234")


def test_parse_recipe_summaries_rejects_incomplete_page():
    with pytest.raises(FatsecretWebParseError, match="declared 3 recipes"):
        FatsecretWebClient._parse_recipe_summaries(_cookbook_html(declared_count=3))


def test_list_recipes_logs_in_and_fetches_cookbook():
    session = Mock()
    session.headers = {}
    auth_url = "https://foods.fatsecret.com/Auth.aspx?pa=s"
    cookbook_url = "https://foods.fatsecret.com/Default.aspx?pa=memc"
    session.get.side_effect = [
        _response(_login_html(), auth_url),
        _response(_cookbook_html(), cookbook_url),
    ]
    session.post.return_value = _response(
        "<html><body>Hello member | Sign out</body></html>", cookbook_url
    )

    client = FatsecretWebClient("member", "secret", session=session)
    recipes = client.list_recipes()

    assert len(recipes) == 2
    payload = session.post.call_args.kwargs["data"]
    assert payload["__VIEWSTATE"] == "state-value"
    assert payload["__VIEWSTATEGENERATOR"] == "generator-value"
    assert payload["ctl00$ctl11$Logincontrol1$Name"] == "member"
    assert payload["ctl00$ctl11$Logincontrol1$Password"] == "secret"
    assert session.get.call_count == 2


def test_login_rejects_unsuccessful_response():
    session = Mock()
    session.headers = {}
    session.get.return_value = _response(
        _login_html(), "https://foods.fatsecret.com/Auth.aspx?pa=s"
    )
    session.post.return_value = _response(
        "<html><body>Sign In</body></html>",
        "https://foods.fatsecret.com/Auth.aspx?pa=s",
    )

    client = FatsecretWebClient("member", "wrong", session=session)
    with pytest.raises(FatsecretWebAuthenticationError):
        client.login()


@pytest.mark.parametrize(
    ("username", "password", "timeout", "message"),
    [
        ("", "secret", 30, "username"),
        ("member", "", 30, "password"),
        ("member", "secret", 0, "timeout"),
    ],
)
def test_constructor_validates_inputs(username, password, timeout, message):
    with pytest.raises(ValueError, match=message):
        FatsecretWebClient(username, password, timeout=timeout)
