"""Parsers for the unsupported FatSecret member food diary."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .errors import FatsecretWebParseError
from .models import (
    WebDiaryEntry,
    WebDiaryItemPortions,
    WebDiaryMeal,
    WebDiaryPortion,
)

DIARY_MEAL_BY_ID = {
    1: WebDiaryMeal.BREAKFAST,
    2: WebDiaryMeal.LUNCH,
    3: WebDiaryMeal.DINNER,
    4: WebDiaryMeal.OTHER,
}
DIARY_MEAL_ID = {meal: meal_id for meal_id, meal in DIARY_MEAL_BY_ID.items()}


@dataclass(frozen=True)
class DiaryEntryReference:
    entry_id: int
    date: int
    edit_url: str


def _query_integer(query: dict[str, list[str]], name: str, *, positive: bool) -> int:
    values = query.get(name, [])
    if not values or not values[0].isdigit():
        raise FatsecretWebParseError(f"diary form has no numeric {name}")
    value = int(values[0])
    if positive and value <= 0:
        raise FatsecretWebParseError(f"diary form has invalid {name}")
    return value


def _required_value(form: Tag, selector: str) -> str:
    field = form.select_one(selector)
    if field is None or field.get("value") is None:
        raise FatsecretWebParseError(f"diary form is missing {selector}")
    return str(field["value"]).strip()


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        normalized = value.strip().replace(",", "")
        parts = normalized.split()
        if len(parts) in {1, 2} and "/" in parts[-1]:
            numerator, denominator = parts[-1].split("/", 1)
            fraction = Decimal(numerator) / Decimal(denominator)
            return (Decimal(parts[0]) + fraction) if len(parts) == 2 else fraction
        return Decimal(normalized)
    except (DecimalException, ValueError) as error:
        raise FatsecretWebParseError(f"invalid {field}: {value!r}") from error


def _portion_options(form: Tag) -> list[WebDiaryPortion]:
    select = form.select_one('select[name="portionid"]')
    if select is None:
        return [WebDiaryPortion(portion_id=0, label="serving", is_grams=False)]

    portions = []
    for option in select.select("option[value]"):
        raw_id = str(option.get("value", ""))
        if not raw_id.lstrip("-").isdigit():
            raise FatsecretWebParseError("diary form contains a non-numeric portion ID")
        label = option.get_text(" ", strip=True)
        portions.append(
            WebDiaryPortion(
                portion_id=int(raw_id),
                label=label,
                is_grams=label.casefold() in {"g", "gram", "grams"},
            )
        )
    if not portions:
        raise FatsecretWebParseError("diary form contains no portions")
    return portions


def parse_diary_entry_references(
    html: str, *, base_url: str, expected_date: int
) -> list[DiaryEntryReference]:
    """Parse unique diary entry links from one daily diary page."""

    soup = BeautifulSoup(html, "lxml")
    references = []
    seen: set[int] = set()
    for link in soup.select('a[href*="pa=fjrd"][href*="eid="]'):
        edit_url = urljoin(base_url, str(link.get("href", "")))
        query = parse_qs(urlparse(edit_url).query)
        entry_id = _query_integer(query, "eid", positive=True)
        date = _query_integer(query, "dt", positive=False)
        if date != expected_date:
            raise FatsecretWebParseError(
                f"diary entry {entry_id} has date {date}, expected {expected_date}"
            )
        if entry_id not in seen:
            references.append(DiaryEntryReference(entry_id, date, edit_url))
            seen.add(entry_id)
    return references


def parse_diary_item_portions(html: str) -> WebDiaryItemPortions:
    """Parse an add-entry form and all portions accepted for its item."""

    soup = BeautifulSoup(html, "lxml")
    form = soup.select_one("form#updateForm")
    if form is None:
        raise FatsecretWebParseError("diary item page has no update form")
    query = parse_qs(urlparse(str(form.get("action", ""))).query)
    return WebDiaryItemPortions(
        item_id=_query_integer(query, "rid", positive=True),
        item_name=_required_value(form, '[name="entryname"]'),
        portions=_portion_options(form),
    )


def parse_diary_entry(html: str, *, edit_url: str) -> WebDiaryEntry:
    """Parse a fully hydrated existing diary entry form."""

    soup = BeautifulSoup(html, "lxml")
    form = soup.select_one("form#updateForm")
    if form is None:
        raise FatsecretWebParseError("diary entry page has no update form")
    query = parse_qs(urlparse(str(form.get("action", ""))).query)
    meal_option = form.select_one('select[name="meal"] option[selected]')
    if meal_option is None or not str(meal_option.get("value", "")).isdigit():
        raise FatsecretWebParseError("diary entry has no selected meal")
    meal_id = int(str(meal_option["value"]))
    if meal_id not in DIARY_MEAL_BY_ID:
        raise FatsecretWebParseError(f"diary entry has unknown meal ID {meal_id}")

    portions = _portion_options(form)
    selected = form.select_one('select[name="portionid"] option[selected]')
    portion = portions[0]
    if selected is not None:
        portion_id = int(str(selected["value"]))
        portion = next(item for item in portions if item.portion_id == portion_id)

    return WebDiaryEntry(
        entry_id=_query_integer(query, "eid", positive=True),
        item_id=_query_integer(query, "rid", positive=True),
        entry_name=_required_value(form, '[name="entryname"]'),
        amount=_decimal(
            _required_value(form, '[name="portionamount"]'), field="diary amount"
        ),
        portion_id=portion.portion_id,
        portion_name=portion.label,
        meal=DIARY_MEAL_BY_ID[meal_id],
        date=_query_integer(query, "dt", positive=False),
        edit_url=edit_url,
    )


__all__ = [
    "DIARY_MEAL_ID",
    "DiaryEntryReference",
    "parse_diary_entry",
    "parse_diary_entry_references",
    "parse_diary_item_portions",
]
