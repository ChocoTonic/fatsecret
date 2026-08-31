"""Tests for unofficial member-account RDI operations."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from fatsecret import (
    FatsecretWebClient,
    FatsecretWebParseError,
    FatsecretWebVerificationError,
)


def _response(text: str, url: str) -> Mock:
    response = Mock()
    response.text = text
    response.url = url
    response.raise_for_status.return_value = None
    return response


def _authenticated_html(body: str = "") -> str:
    return f"<html><body>Hello member | Sign out {body}</body></html>"


def _diary_html(rdi: int, effective_date: str = "20 Aug 26") -> str:
    return _authenticated_html(
        f"<div>* Based on your RDI of {rdi:,} calories ({effective_date})</div>"
    )


def _settings_html() -> str:
    return _authenticated_html("""
        <form>
          <input type="hidden" name="__VIEWSTATE" value="settings-state">
          <input type="hidden" name="__EVENTVALIDATION" value="validation">
          <select name="ctl00$ctl11$Goal">
            <option value="3" selected>Maintain</option>
          </select>
          <input name="ctl00$ctl11$PhysicalLevel" value="2" checked>
          <a href="javascript:__doPostBack('ctl00$ctl11$ctl08','')">
            Calculate my RDI
          </a>
        </form>
        """)


def _calculated_html() -> str:
    return _authenticated_html("""
        <form>
          <input type="hidden" name="__VIEWSTATE" value="calculated-state">
          <input name="ctl00$ctl11$RDI" value="2700">
          <a href="javascript:__doPostBack('ctl00$ctl11$ctl13','')">Save</a>
        </form>
        """)


def _rdi_client(*, readback_rdi: int = 1800) -> tuple[FatsecretWebClient, Mock]:
    session = Mock()
    session.headers = {}
    cookbook_url = "https://foods.fatsecret.com/Default.aspx?pa=memc"
    diary_url = "https://foods.fatsecret.com/Diary.aspx?pa=fj"
    settings_url = "https://foods.fatsecret.com/Default.aspx?pa=cmrdi"
    session.get.side_effect = [
        _response(_authenticated_html(), cookbook_url),
        _response(_diary_html(1676), diary_url),
        _response(_settings_html(), settings_url),
        _response(_diary_html(readback_rdi), diary_url),
    ]
    session.post.side_effect = [
        _response(_calculated_html(), settings_url),
        _response(_diary_html(readback_rdi), diary_url),
    ]
    return FatsecretWebClient("member", "secret", session=session), session


def test_get_rdi_returns_saved_value_and_effective_date():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(
            _authenticated_html(), "https://foods.fatsecret.com/Default.aspx?pa=memc"
        ),
        _response(_diary_html(1_676), "https://foods.fatsecret.com/Diary.aspx?pa=fj"),
    ]

    setting = FatsecretWebClient("member", "secret", session=session).get_rdi()

    assert setting.calories_per_day == 1676
    assert setting.effective_date == date(2026, 8, 20)


def test_get_rdi_fails_when_footer_shape_changes():
    session = Mock()
    session.headers = {}
    session.get.side_effect = [
        _response(
            _authenticated_html(), "https://foods.fatsecret.com/Default.aspx?pa=memc"
        ),
        _response(
            _authenticated_html("No RDI here"),
            "https://foods.fatsecret.com/Diary.aspx?pa=fj",
        ),
    ]

    with pytest.raises(FatsecretWebParseError, match="saved-RDI footer"):
        FatsecretWebClient("member", "secret", session=session).get_rdi()


def test_set_rdi_preserves_profile_selections_and_verifies_readback():
    client, session = _rdi_client()

    result = client.set_rdi(1800)

    assert result.previous.calories_per_day == 1676
    assert result.current.calories_per_day == 1800
    assert result.requested_calories_per_day == 1800
    assert session.post.call_count == 2

    calculate = session.post.call_args_list[0].kwargs["data"]
    assert calculate["__EVENTTARGET"] == "ctl00$ctl11$ctl08"
    assert calculate["ctl00$ctl11$Goal"] == "3"
    assert calculate["ctl00$ctl11$PhysicalLevel"] == "2"
    assert calculate["__EVENTVALIDATION"] == "validation"

    save = session.post.call_args_list[1].kwargs["data"]
    assert save["__EVENTTARGET"] == "ctl00$ctl11$ctl13"
    assert save["ctl00$ctl11$RDI"] == "1800"


def test_set_rdi_raises_when_readback_does_not_match():
    client, session = _rdi_client(readback_rdi=1750)

    with pytest.raises(FatsecretWebVerificationError, match="read back 1750"):
        client.set_rdi(1800)

    assert session.post.call_count == 2


def test_set_rdi_marks_an_unauthenticated_save_response_as_ambiguous():
    client, session = _rdi_client(readback_rdi=1676)
    session.post.side_effect = [
        _response(
            _calculated_html(), "https://foods.fatsecret.com/Default.aspx?pa=cmrdi"
        ),
        _response(
            "<html><body>Sign In</body></html>",
            "https://foods.fatsecret.com/Auth.aspx?pa=s",
        ),
    ]

    with pytest.raises(FatsecretWebVerificationError, match="outcome is unknown"):
        client.set_rdi(1676)

    assert session.get.call_count == 3


@pytest.mark.parametrize("value", [0, -1, 100_001])
def test_set_rdi_rejects_out_of_range_values(value):
    client, session = _rdi_client()

    with pytest.raises(ValueError, match="between"):
        client.set_rdi(value)

    session.get.assert_not_called()


@pytest.mark.parametrize("value", [True, 1800.5, "1800"])
def test_set_rdi_requires_an_integer(value):
    client, session = _rdi_client()

    with pytest.raises(TypeError, match="integer"):
        client.set_rdi(value)

    session.get.assert_not_called()
