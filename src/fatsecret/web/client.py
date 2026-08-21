"""Unofficial client for authenticated FatSecret member-website operations.

This targets ``foods.fatsecret.com``, not the supported Platform API. Its HTML
contract can change without notice, so it remains separate from generated API
resources and verifies every account-setting write by reading it back.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from ..fatsecret import _user_agent
from .errors import (
    FatsecretWebAuthenticationError,
    FatsecretWebParseError,
    FatsecretWebVerificationError,
)
from .models import (
    WebRdiSetting,
    WebRdiUpdate,
    WebRecipeSummary,
    WebRecipeSummaryNutrition,
)


class FatsecretWebClient:
    """Cookie-authenticated client for one FatSecret member account.

    Credentials are retained only in memory so an expired session can be
    authenticated again. Source them from environment variables or an OS
    keychain rather than passing them through an MCP tool invocation.
    """

    BASE_URL = "https://foods.fatsecret.com"
    COOKBOOK_PATH = "/Default.aspx?pa=memc"
    DIARY_PATH = "/Diary.aspx?pa=fj"
    RDI_SETTINGS_PATH = (
        "/Default.aspx?pa=cmrdi"
        "&ReturnUrl=https%3a%2f%2ffoods.fatsecret.com%2fDiary.aspx%3fpa%3dfj"
    )

    _SUMMARY_NUTRITION_RE = re.compile(
        r"cals:\s*(?P<calories>[\d,.]+)\s*kcal\s*\|\s*"
        r"fat:\s*(?P<fat>[\d,.]+)\s*g\s*\|\s*"
        r"carbs:\s*(?P<carbohydrate>[\d,.]+)\s*g\s*\|\s*"
        r"prot:\s*(?P<protein>[\d,.]+)\s*g",
        re.IGNORECASE,
    )
    _SUBMITTED_COUNT_RE = re.compile(
        r"submitted\s+(?P<count>\d+)\s+recipes?", re.IGNORECASE
    )
    _RDI_RE = re.compile(
        r"RDI of (?P<calories>[\d,]+)\s*calories\s*\((?P<date>[^)]+)\)",
        re.IGNORECASE,
    )
    _POSTBACK_RE = re.compile(r"__doPostBack\('(?P<target>[^']+)'\s*,")

    def __init__(
        self,
        username: str,
        password: str,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 30,
    ) -> None:
        if not username:
            raise ValueError("username must not be empty")
        if not password:
            raise ValueError("password must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self._username = username
        self._password = password
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", _user_agent())
        self._timeout = timeout
        self._authenticated = False

    @property
    def cookbook_url(self) -> str:
        return urljoin(self.BASE_URL, self.COOKBOOK_PATH)

    @property
    def diary_url(self) -> str:
        return urljoin(self.BASE_URL, self.DIARY_PATH)

    @property
    def rdi_settings_url(self) -> str:
        return urljoin(self.BASE_URL, self.RDI_SETTINGS_PATH)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "FatsecretWebClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def login(self) -> None:
        """Authenticate against the ASP.NET member-site login form."""

        login_page = self._session.get(self.cookbook_url, timeout=self._timeout)
        login_page.raise_for_status()
        if self._is_authenticated(login_page.text):
            self._authenticated = True
            return

        soup = BeautifulSoup(login_page.text, "lxml")
        payload = {
            **self._hidden_fields(soup),
            "__EVENTTARGET": "ctl00$ctl11$Logincontrol1$Login",
            "__EVENTARGUMENT": "",
            "ctl00$ctl11$Logincontrol1$Name": self._username,
            "ctl00$ctl11$Logincontrol1$Password": self._password,
            "ctl00$ctl11$Logincontrol1$CreatePersistentCookie": "on",
        }
        response = self._session.post(
            login_page.url,
            data=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        if not self._is_authenticated(response.text):
            raise FatsecretWebAuthenticationError(
                "FatSecret member login failed; credentials or login form may have changed"
            )
        self._authenticated = True

    def list_recipes(self) -> list[WebRecipeSummary]:
        """Return summary metadata for every recipe owned by the member."""

        response = self._get_authenticated(self.cookbook_url)
        return self._parse_recipe_summaries(response.text)

    def get_rdi(self) -> WebRdiSetting:
        """Return the RDI currently saved to the member account."""

        response = self._get_authenticated(self.diary_url)
        match = self._RDI_RE.search(response.text)
        if match is None:
            raise FatsecretWebParseError(
                "FatSecret diary does not contain the expected saved-RDI footer"
            )
        try:
            effective_date = datetime.strptime(
                match.group("date").strip(), "%d %b %y"
            ).date()
        except ValueError as error:
            raise FatsecretWebParseError(
                f"unknown FatSecret RDI effective date: {match.group('date')!r}"
            ) from error
        return WebRdiSetting(
            calories_per_day=int(match.group("calories").replace(",", "")),
            effective_date=effective_date,
        )

    def set_rdi(self, calories_per_day: int) -> WebRdiUpdate:
        """Replace the saved RDI and return the verified before/after state.

        The website requires a calculator transition before Save. This method
        preserves the account's current goal and physical-activity selections;
        they are implementation details rather than part of this API. The Save
        request is never retried automatically.
        """

        if isinstance(calories_per_day, bool) or not isinstance(calories_per_day, int):
            raise TypeError("calories_per_day must be an integer")
        if not 1 <= calories_per_day <= 100_000:
            raise ValueError("calories_per_day must be between 1 and 100000")

        previous = self.get_rdi()
        settings_response = self._get_authenticated(self.rdi_settings_url)
        settings = BeautifulSoup(settings_response.text, "lxml")
        goal = self._selected_value(settings, 'select[name$="$Goal"] option[selected]')
        physical_level = self._selected_value(
            settings, 'input[name$="$PhysicalLevel"][checked]'
        )

        calculate_payload = {
            **self._hidden_fields(settings),
            "__EVENTTARGET": self._postback_target(settings, "Calculate my RDI"),
            "__EVENTARGUMENT": "",
            "ctl00$ctl11$Goal": goal,
            "ctl00$ctl11$PhysicalLevel": physical_level,
        }
        calculated_response = self._session.post(
            self.rdi_settings_url,
            data=calculate_payload,
            headers={"Referer": self.rdi_settings_url},
            timeout=self._timeout,
        )
        calculated_response.raise_for_status()
        if not self._is_authenticated(calculated_response.text):
            self._authenticated = False
            raise FatsecretWebAuthenticationError(
                "FatSecret member session expired during the RDI calculator transition"
            )

        calculated = BeautifulSoup(calculated_response.text, "lxml")
        if calculated.select_one('input[name$="$RDI"]') is None:
            raise FatsecretWebParseError(
                "FatSecret RDI calculator response has no editable RDI field"
            )
        save_payload = {
            **self._hidden_fields(calculated),
            "__EVENTTARGET": self._postback_target(calculated, "Save"),
            "__EVENTARGUMENT": "",
            "ctl00$ctl11$RDI": str(calories_per_day),
        }
        save_response = self._session.post(
            self.rdi_settings_url,
            data=save_payload,
            headers={"Referer": self.rdi_settings_url},
            timeout=self._timeout,
        )
        save_response.raise_for_status()
        if not self._is_authenticated(save_response.text):
            self._authenticated = False
            raise FatsecretWebAuthenticationError(
                "FatSecret member session expired while saving the RDI"
            )
        if "Diary.aspx" not in save_response.url:
            raise FatsecretWebVerificationError(
                "FatSecret RDI save did not return to the diary; outcome is unknown"
            )

        current = self.get_rdi()
        if current.calories_per_day != calories_per_day:
            raise FatsecretWebVerificationError(
                "FatSecret RDI save could not be verified: requested "
                f"{calories_per_day}, read back {current.calories_per_day}"
            )
        return WebRdiUpdate(
            requested_calories_per_day=calories_per_day,
            previous=previous,
            current=current,
        )

    def _get_authenticated(self, url: str) -> requests.Response:
        if not self._authenticated:
            self.login()
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        if self._is_authenticated(response.text):
            return response

        self._authenticated = False
        self.login()
        response = self._session.get(url, timeout=self._timeout)
        response.raise_for_status()
        if not self._is_authenticated(response.text):
            raise FatsecretWebAuthenticationError(
                "FatSecret member session expired during page retrieval"
            )
        return response

    @classmethod
    def _parse_recipe_summaries(cls, html: str) -> list[WebRecipeSummary]:
        soup = BeautifulSoup(html, "lxml")
        page_text = soup.get_text(" ", strip=True)
        count_match = cls._SUBMITTED_COUNT_RE.search(page_text)
        expected_count = int(count_match.group("count")) if count_match else None

        summaries: list[WebRecipeSummary] = []
        seen_ids: set[int] = set()
        for row in soup.select("td.borderBottom"):
            edit_link = row.select_one(
                'a[href*="Diary.aspx?pa=mrece"][href*="recipeid="]'
            )
            if edit_link is None:
                continue

            recipe_id = cls._recipe_id_from_edit_link(edit_link)
            if recipe_id in seen_ids:
                raise FatsecretWebParseError(
                    f"duplicate recipe id {recipe_id} in cookbook response"
                )
            seen_ids.add(recipe_id)

            heading = row.select_one("h2.prominent")
            title_link = heading.select_one("a") if heading else None
            status_tag = heading.select_one("span.smallText") if heading else None
            description_tag = row.select_one("div.greyText")
            nutrition_tag = row.select_one('div.smallText[style*="font-weight:bold"]')
            if not all((title_link, status_tag, description_tag, nutrition_tag)):
                raise FatsecretWebParseError(
                    f"recipe {recipe_id} cookbook row is missing required metadata"
                )

            nutrition_match = cls._SUMMARY_NUTRITION_RE.search(
                nutrition_tag.get_text(" ", strip=True)
            )
            if nutrition_match is None:
                raise FatsecretWebParseError(
                    f"recipe {recipe_id} nutrition summary has an unknown format"
                )

            description = description_tag.get_text(" ", strip=True)
            if len(description) >= 2 and description[0] == description[-1] == '"':
                description = description[1:-1]

            summaries.append(
                WebRecipeSummary(
                    recipe_id=recipe_id,
                    title=title_link.get_text(" ", strip=True),
                    description=description,
                    status=status_tag.get_text(" ", strip=True).strip("()"),
                    nutrition=WebRecipeSummaryNutrition(
                        calories=cls._decimal(nutrition_match.group("calories")),
                        fat_g=cls._decimal(nutrition_match.group("fat")),
                        carbohydrate_g=cls._decimal(
                            nutrition_match.group("carbohydrate")
                        ),
                        protein_g=cls._decimal(nutrition_match.group("protein")),
                    ),
                    preview_url=urljoin(cls.BASE_URL, title_link.get("href", "")),
                    edit_url=urljoin(cls.BASE_URL, edit_link.get("href", "")),
                )
            )

        if expected_count is not None and expected_count != len(summaries):
            raise FatsecretWebParseError(
                "cookbook declared "
                f"{expected_count} recipes but {len(summaries)} recipe rows were parsed"
            )
        return summaries

    def _is_authenticated(self, html: str) -> bool:
        text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
        return self._username in text and "Sign out" in text

    @staticmethod
    def _hidden_fields(soup: BeautifulSoup) -> dict[str, str]:
        return {
            str(field["name"]): str(field.get("value", ""))
            for field in soup.select('input[type="hidden"][name]')
        }

    @staticmethod
    def _selected_value(soup: BeautifulSoup, selector: str) -> str:
        field = soup.select_one(selector)
        if field is None or field.get("value") is None:
            raise FatsecretWebParseError(
                f"FatSecret RDI form is missing selected field {selector}"
            )
        return str(field["value"])

    @classmethod
    def _postback_target(cls, soup: BeautifulSoup, label: str) -> str:
        for link in soup.select("a[href]"):
            if link.get_text(" ", strip=True).casefold() != label.casefold():
                continue
            match = cls._POSTBACK_RE.search(str(link.get("href", "")))
            if match:
                return match.group("target")
        raise FatsecretWebParseError(
            f"FatSecret form has no {label!r} postback control"
        )

    @staticmethod
    def _recipe_id_from_edit_link(link: Tag) -> int:
        query = parse_qs(urlparse(link.get("href", "")).query)
        values = query.get("recipeid")
        if not values or not values[0].isdigit():
            raise FatsecretWebParseError("cookbook edit link has no numeric recipeid")
        return int(values[0])

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            return Decimal(value.replace(",", ""))
        except InvalidOperation as error:
            raise FatsecretWebParseError(
                f"invalid decimal value in cookbook: {value!r}"
            ) from error
