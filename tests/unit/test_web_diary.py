"""Member food-diary parsing, mutation, and verification tests."""

from decimal import Decimal
from unittest.mock import Mock

import pytest
import requests

from fatsecret import (
    FatsecretWebClient,
    WebDiaryEntryWrite,
    WebDiaryMeal,
)
from fatsecret.web.diary_parser import (
    parse_diary_entry,
    parse_diary_entry_references,
    parse_diary_item_portions,
)

BASE = "https://foods.fatsecret.com"


def _response(text: str, url: str, status_code: int = 200) -> Mock:
    response = Mock()
    response.text = text
    response.url = url
    response.status_code = status_code
    response.headers = {}
    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(response=response)
    else:
        response.raise_for_status.return_value = None
    return response


def _auth(body: str) -> str:
    return f"<html><body>Hello member | Sign out {body}</body></html>"


def _diary(*entry_ids: int) -> str:
    links = "".join(
        f'<a href="/Diary.aspx?pa=fjrd&amp;eid={entry_id}&amp;dt=20699">item</a>'
        for entry_id in entry_ids
    )
    return _auth(links)


def _entry_form(
    *, entry_id: int = 501, recipe: bool = False, amount: str | None = None
) -> str:
    portion = (
        "serving(s)"
        if recipe
        else '<select name="portionid"><option value="12">4 oz</option>'
        '<option selected value="-1">g</option></select>'
    )
    item_id = 101 if recipe else 201
    amount = amount or ("259" if recipe else "159")
    name = "Pasta" if recipe else "Chicken"
    return _auth(f"""
      <form id="updateForm" action="/Diary.aspx?pa=fjrd&amp;dt=20699&amp;rid={item_id}&amp;eid={entry_id}">
        <select name="meal"><option value="1">Breakfast</option><option selected value="3">Dinner</option></select>
        <input name="entryname" value="{name}">
        <input name="portionamount" value="{amount}">
        {portion}
      </form>
    """)


def _add_form(*, recipe: bool = False) -> str:
    portion = (
        "serving(s)"
        if recipe
        else '<select name="portionid"><option value="12">4 oz</option>'
        '<option value="-1">g</option></select>'
    )
    item_id = 101 if recipe else 201
    name = "Pasta" if recipe else "Chicken"
    return _auth(f"""
      <form id="updateForm" action="/Diary.aspx?pa=fjrd&amp;dt=20699&amp;rid={item_id}">
        <select name="meal"><option selected value="1">Breakfast</option></select>
        <input name="entryname" value="{name}">
        <input name="portionamount" value="1">
        {portion}
      </form>
    """)


def _client(session: Mock) -> FatsecretWebClient:
    session.headers = {}
    client = FatsecretWebClient("member", "secret", session=session)
    client._authenticated = True
    return client


def test_diary_parsers_preserve_recipe_and_gram_sentinel_portions():
    references = parse_diary_entry_references(
        _diary(501), base_url=BASE, expected_date=20699
    )
    recipe_portions = parse_diary_item_portions(_add_form(recipe=True))
    food_entry = parse_diary_entry(
        _entry_form(), edit_url=f"{BASE}/Diary.aspx?pa=fjrd&eid=501&dt=20699"
    )

    assert references[0].entry_id == 501
    assert recipe_portions.portions[0].portion_id == 0
    assert food_entry.portion_id == -1
    assert food_entry.item_id == 201


def test_diary_parser_accepts_rendered_mixed_fraction_amounts():
    entry = parse_diary_entry(
        _entry_form(amount="1 1/4"),
        edit_url=f"{BASE}/Diary.aspx?pa=fjrd&eid=501&dt=20699",
    )

    assert entry.amount == Decimal("1.25")


def test_add_owned_recipe_to_diary_posts_and_verifies():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(_diary(), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(
            _add_form(recipe=True), f"{BASE}/Diary.aspx?pa=fjrd&rid=101&dt=20699"
        ),
        _response(_diary(501), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(
            _entry_form(recipe=True), f"{BASE}/Diary.aspx?pa=fjrd&eid=501&dt=20699"
        ),
    ]
    session.post.return_value = _response(
        _diary(501), f"{BASE}/Diary.aspx?pa=fj&dt=20699"
    )

    result = _client(session).add_diary_entry(
        WebDiaryEntryWrite(
            item_id=101,
            entry_name="Pasta",
            amount=Decimal("259"),
            meal=WebDiaryMeal.DINNER,
            date=20699,
        )
    )

    assert result.entry_id == 501
    assert result.portion_id == 0
    payload = session.post.call_args.kwargs["data"]
    assert payload["meal"] == "3"
    assert payload["portionamount"] == "259"
    assert "portionid" not in payload


def test_fractional_grams_are_rejected_before_diary_write():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(_diary(), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(_add_form(), f"{BASE}/Diary.aspx?pa=fjrd&rid=201&dt=20699"),
    ]

    with pytest.raises(ValueError, match="whole numbers"):
        _client(session).add_diary_entry(
            WebDiaryEntryWrite(
                item_id=201,
                entry_name="Chicken",
                amount=Decimal("159.3"),
                meal=WebDiaryMeal.LUNCH,
                date=20699,
            )
        )

    session.post.assert_not_called()


def test_delete_diary_entry_is_verified_and_idempotent():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(_diary(501), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(_diary(), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(_diary(), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
        _response(_diary(), f"{BASE}/Diary.aspx?pa=fj&dt=20699"),
    ]
    client = _client(session)

    first = client.delete_diary_entry(501, 20699)
    second = client.delete_diary_entry(501, 20699)

    assert first.deleted is True
    assert second.deleted is False
    assert "action=deleteentry" in session.get.call_args_list[1].args[0]
