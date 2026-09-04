"""Request sequencing and verification tests for member recipe CRUD."""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

from fatsecret import (
    FatsecretWebClient,
    FatsecretWebVerificationError,
    WebIngredientWrite,
    WebRecipeWrite,
)


def _response(text: str, url: str, status_code: int = 200) -> Mock:
    response = Mock()
    response.text = text
    response.url = url
    response.status_code = status_code
    response.headers = {}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}", response=response
        )
    else:
        response.raise_for_status.return_value = None
    return response


def _auth(body: str) -> str:
    return f"<html><body>Hello member | Sign out {body}</body></html>"


def _cookbook(*, include_recipe: bool = True) -> str:
    if not include_recipe:
        return _auth("<div>you have submitted 0 recipes</div>")
    return _auth("""
        <input type="hidden" name="__VIEWSTATE" value="state">
        <div>you have submitted 1 recipe</div>
        <td class="borderBottom">
          <h2 class="prominent"><a href="/recipes/one">Bean Stew</a>
          <span class="smallText">(Pending)</span></h2>
          <div class="smallText" style="font-weight:bold">cals: 100kcal | fat: 1g | carbs: 20g | prot: 5g</div>
          <div class="greyText">"Description"</div>
          <a href="/Diary.aspx?pa=mrece&amp;recipeid=101">edit recipe</a>
          <a href="javascript:__doPostBack('ctl00$delete101','')" title="delete recipe">delete</a>
        </td>
        """)


def _edit(*, with_ingredient: bool = False) -> str:
    ingredient = ""
    if with_ingredient:
        ingredient = """
        <td class="borderBottom"><table><tr valign="top">
          <td><a title="edit" href="/Diary.aspx?pa=fjrd&amp;prid=101&amp;iid=501">15 g beans</a></td>
          <td class="greyback">1</td><td class="greyback">20</td>
          <td class="greyback">5</td><td class="greyback">2</td>
          <td class="greyback">5</td><td class="greyback">100</td>
        </tr></table></td>
        """
    return _auth(f"""
        <form id="dtform">
          <input name="title" value="Bean Stew">
          <textarea name="description">Description</textarea>
          <input name="portions" value="4">
          <input name="prepTime" value="5">
          <input name="cookTime" value="10">
        </form>
        <textarea name="step1">Cook.</textarea>
        {ingredient}
        """)


def _ingredient_detail() -> str:
    return _auth("""
        <form id="updateFormOther" action="/Diary.aspx?pa=fjrd&amp;rid=201&amp;prid=101&amp;iid=501">
          <input name="entryname" value="Beans">
          <input name="portionamount" value="15">
          <select name="portionid"><option selected value="301">g</option></select>
        </form>
        """)


def _write() -> WebRecipeWrite:
    return WebRecipeWrite(
        title="Bean Stew",
        description="Description",
        servings=Decimal("4"),
        prep_minutes=5,
        cook_minutes=10,
        meal_types=[],
        directions=["Cook."],
    )


def _client(session: Mock) -> FatsecretWebClient:
    session.headers = {}
    client = FatsecretWebClient("member", "secret", session=session)
    client._authenticated = True
    return client


def test_create_recipe_posts_full_form_and_verifies_readback():
    session = Mock()
    session.headers = {}
    session.post.return_value = _response(
        _edit(),
        "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101&xpnd=True",
    )
    session.get.side_effect = [
        _response(_cookbook(), "https://foods.fatsecret.com/Default.aspx?pa=memc"),
        _response(
            _edit(), "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101"
        ),
    ]

    created = _client(session).create_recipe(_write())

    assert created.recipe_id == 101
    payload = session.post.call_args.kwargs["data"]
    assert payload["title"] == "Bean Stew"
    assert payload["portions"] == "4"
    assert payload["step1"] == "Cook."
    assert payload["step8"] == ""


def test_add_ingredient_resolves_grams_and_verifies_new_entry():
    session = Mock()
    session.headers = {}
    portions = """
    <input name="entryname" value="Beans">
    <select name="portionid"><option value="301">g</option></select>
    """
    session.get.side_effect = [
        _response(
            _edit(), "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101"
        ),
        _response(
            portions, "https://foods.fatsecret.com/ajax/RecipePortionOptions.aspx"
        ),
        _response(
            _edit(with_ingredient=True),
            "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
        ),
        _response(
            _ingredient_detail(),
            "https://foods.fatsecret.com/Diary.aspx?pa=fjrd&prid=101&iid=501",
        ),
    ]
    session.post.return_value = _response(
        _edit(with_ingredient=True),
        "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
    )

    added = _client(session).add_recipe_ingredient(
        101, WebIngredientWrite(food_id=201, amount=Decimal("15"))
    )

    assert added.entry_id == 501
    assert added.portion_id == 301
    payload = session.post.call_args.kwargs["data"]
    assert payload["recipeid"] == "201"
    assert payload["portionid"] == "301"


def test_add_ingredient_rejects_fractional_grams_before_post():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(
            _edit(), "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101"
        ),
        _response(
            '<input name="entryname" value="Beans"><select name="portionid"><option value="-1">g</option></select>',
            "https://foods.fatsecret.com/ajax/RecipePortionOptions.aspx",
        ),
    ]

    with pytest.raises(ValueError, match="whole numbers"):
        _client(session).add_recipe_ingredient(
            101, WebIngredientWrite(food_id=201, amount=Decimal("15.5"))
        )

    session.post.assert_not_called()


def test_delete_recipe_posts_row_specific_target_and_verifies_absence():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(_cookbook(), "https://foods.fatsecret.com/Default.aspx?pa=memc"),
        _response(
            _cookbook(include_recipe=False),
            "https://foods.fatsecret.com/Default.aspx?pa=memc",
        ),
    ]
    session.post.return_value = _response(
        _cookbook(include_recipe=False),
        "https://foods.fatsecret.com/Default.aspx?pa=memc",
    )

    result = _client(session).delete_recipe(101)

    assert result.deleted is True
    payload = session.post.call_args.kwargs["data"]
    assert payload["__EVENTTARGET"] == "ctl00$delete101"
    assert payload["__VIEWSTATE"] == "state"


def test_add_ingredient_maps_rate_limited_readback_to_ambiguous_outcome():
    session = Mock()
    session.headers = {}
    rate_limited = _response(
        "rate limited", "https://foods.fatsecret.com/Diary.aspx", 429
    )
    rate_limited.headers = {"Retry-After": "120"}
    session.get.side_effect = [
        _response(
            _edit(), "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101"
        ),
        _response(
            '<input name="entryname" value="Beans"><select name="portionid"><option value="301">g</option></select>',
            "https://foods.fatsecret.com/ajax/RecipePortionOptions.aspx",
        ),
        rate_limited,
        rate_limited,
        rate_limited,
    ]
    session.post.return_value = _response(
        _edit(with_ingredient=True),
        "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
    )

    with patch("time.sleep") as sleep_mock:
        with pytest.raises(FatsecretWebVerificationError) as caught:
            _client(session).add_recipe_ingredient(
                101, WebIngredientWrite(food_id=201, amount=Decimal("15"))
            )

    assert caught.value.retry_after == 120
    assert "outcome is unknown" in str(caught.value)
    assert [call.args[0] for call in sleep_mock.call_args_list] == [120.0, 120.0]


def test_mutation_waits_for_explicit_retry_after_before_replaying():
    session = Mock()
    session.headers = {}
    limited = _response("rate limited", "https://example.test/write", 429)
    limited.headers = {"Retry-After": "120"}
    accepted = _response(_auth(""), "https://example.test/write")
    session.post.side_effect = [limited, accepted]
    client = _client(session)

    with patch("time.sleep") as sleep_mock:
        response = client._post_mutation(
            "https://example.test/write",
            data={"value": "1"},
            referer="https://example.test/edit",
            operation="testing a write",
        )

    assert response is accepted
    sleep_mock.assert_called_once_with(120)
    assert session.post.call_count == 2


def test_mutation_uses_configured_fallback_when_retry_after_is_missing():
    session = Mock()
    session.headers = {}
    limited = _response("rate limited", "https://example.test/write", 429)
    accepted = _response(_auth(""), "https://example.test/write")
    session.post.side_effect = [limited, accepted]
    client = FatsecretWebClient(
        "member", "secret", session=session, default_retry_after=45
    )
    client._authenticated = True

    with patch("time.sleep") as sleep_mock:
        client._post_mutation(
            "https://example.test/write",
            data={"value": "1"},
            referer="https://example.test/edit",
            operation="testing a write",
        )

    sleep_mock.assert_called_once_with(45)


def test_replace_ingredient_submits_the_form_save_action():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(
            _edit(with_ingredient=True),
            "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
        ),
        _response(
            '<input name="entryname" value="Beans"><select name="portionid"><option value="301">g</option></select>',
            "https://foods.fatsecret.com/ajax/RecipePortionOptions.aspx",
        ),
        _response(
            _edit(with_ingredient=True),
            "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
        ),
        _response(
            _ingredient_detail(),
            "https://foods.fatsecret.com/Diary.aspx?pa=fjrd&prid=101&iid=501",
        ),
    ]
    session.post.return_value = _response(
        _edit(with_ingredient=True),
        "https://foods.fatsecret.com/Diary.aspx?pa=mrece&recipeid=101",
    )

    _client(session).replace_recipe_ingredient(
        101,
        501,
        WebIngredientWrite(food_id=201, amount=Decimal("15"), portion_id=301),
    )

    assert session.post.call_args.kwargs["data"]["action"] == "Save"
    assert session.post.call_args.kwargs["headers"] == {
        "Origin": "https://foods.fatsecret.com",
        "Referer": "https://foods.fatsecret.com/Diary.aspx?pa=fjrd&prid=101&iid=501",
    }
