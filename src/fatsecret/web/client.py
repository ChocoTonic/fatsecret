"""Unofficial client for authenticated FatSecret member-website operations.

This targets ``foods.fatsecret.com``, not the supported Platform API. Its HTML
contract can change without notice, so it remains separate from generated API
resources and verifies every account-setting write by reading it back.
"""

from __future__ import annotations

import re
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

from .._retry import RetryPolicy, parse_retry_after, resolve_retry_policy
from ..fatsecret import _user_agent
from .errors import (
    FatsecretWebAuthenticationError,
    FatsecretWebNotFoundError,
    FatsecretWebParseError,
    FatsecretWebRateLimitError,
    FatsecretWebVerificationError,
)
from .diary_parser import (
    DIARY_MEAL_ID,
    DiaryEntryReference,
    parse_diary_entry,
    parse_diary_entry_references,
    parse_diary_item_portions,
)
from .models import (
    WebDiaryEntry,
    WebDiaryEntryDeleteResult,
    WebDiaryEntryWrite,
    WebDiaryItemPortions,
    WebDiaryPortion,
    WebFoodPortions,
    WebIngredientWrite,
    WebRdiSetting,
    WebRdiUpdate,
    WebRecipeDeleteResult,
    WebRecipeDetail,
    WebRecipeIngredient,
    WebRecipeSummary,
    WebRecipeSummaryNutrition,
    WebRecipeWrite,
)
from .recipe_parser import (
    RecipeEditPage,
    metadata_matches,
    parse_food_portions,
    parse_ingredient_detail,
    parse_recipe_edit_page,
    recipe_form_payload,
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
    DIARY_ENTRY_PATH = "/Diary.aspx?pa=fjrd"
    RECIPE_EDIT_PATH = "/Diary.aspx?pa=mrece&recipeid={recipe_id}"
    PORTION_OPTIONS_PATH = "/ajax/RecipePortionOptions.aspx"
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
        retries: RetryPolicy = True,
        wait_on_rate_limit: bool = True,
        default_retry_after: int = 300,
    ) -> None:
        if not username:
            raise ValueError("username must not be empty")
        if not password:
            raise ValueError("password must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if default_retry_after <= 0:
            raise ValueError("default_retry_after must be greater than zero")

        self._username = username
        self._password = password
        self._session = session or requests.Session()
        self._session.headers.setdefault("User-Agent", _user_agent())
        self._timeout = timeout
        self._retries = resolve_retry_policy(retries)
        self._wait_on_rate_limit = wait_on_rate_limit
        self._default_retry_after = default_retry_after
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

        login_page = self._get(self.cookbook_url)
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
        self._raise_for_status(response)
        if not self._is_authenticated(response.text):
            raise FatsecretWebAuthenticationError(
                "FatSecret member login failed; credentials or login form may have changed"
            )
        self._authenticated = True

    def list_recipes(self) -> list[WebRecipeSummary]:
        """Return summary metadata for every recipe owned by the member."""

        response = self._get_authenticated(self.cookbook_url)
        return self._parse_recipe_summaries(response.text)

    def list_diary_entries(self, date: int) -> list[WebDiaryEntry]:
        """Return fully hydrated member food-diary entries for one epoch-day."""

        date = self._nonnegative_id(date, "date")
        return [
            self._hydrate_diary_entry(reference)
            for reference in self._get_diary_references(date)
        ]

    def get_diary_entry(self, entry_id: int, date: int) -> WebDiaryEntry:
        """Return one member food-diary entry and verify its requested date."""

        entry_id = self._positive_id(entry_id, "entry_id")
        date = self._nonnegative_id(date, "date")
        reference = next(
            (
                item
                for item in self._get_diary_references(date)
                if item.entry_id == entry_id
            ),
            None,
        )
        if reference is None:
            raise FatsecretWebNotFoundError(
                f"member diary entry {entry_id} was not found on date {date}"
            )
        return self._hydrate_diary_entry(reference)

    def list_diary_item_portions(self, item_id: int, date: int) -> WebDiaryItemPortions:
        """Return diary portions for a known food or owned member recipe ID."""

        item_id = self._positive_id(item_id, "item_id")
        date = self._nonnegative_id(date, "date")
        response = self._get_authenticated(self._diary_item_url(item_id, date))
        portions = parse_diary_item_portions(response.text)
        if portions.item_id != item_id:
            raise FatsecretWebVerificationError(
                f"diary portion form resolved item {portions.item_id}, expected {item_id}"
            )
        return portions

    def add_diary_entry(self, entry: WebDiaryEntryWrite) -> WebDiaryEntry:
        """Add one food or owned recipe to the member diary and verify it."""

        entry = WebDiaryEntryWrite.model_validate(entry)
        before = self._get_diary_references(entry.date)
        portions = self.list_diary_item_portions(entry.item_id, entry.date)
        portion = self._select_diary_portion(portions, entry.portion_id)
        self._require_supported_diary_amount(entry.amount, portion)
        referer = self._diary_item_url(entry.item_id, entry.date)
        data = {
            "dtb": str(entry.date),
            "meal": str(DIARY_MEAL_ID[entry.meal]),
            "entryname": entry.entry_name,
            "portionamount": format(entry.amount, "f"),
            "action": "Save",
        }
        if portion.portion_id != 0:
            data["portionid"] = str(portion.portion_id)
        self._post_mutation(
            referer,
            data=data,
            referer=referer,
            operation=f"adding diary entry on date {entry.date}",
        )
        before_ids = {item.entry_id for item in before}
        after = self._read_after_write(
            lambda: self._get_diary_references(entry.date),
            operation=f"adding diary entry on date {entry.date}",
        )
        added = [item for item in after if item.entry_id not in before_ids]
        if len(added) != 1:
            raise FatsecretWebVerificationError(
                f"diary add on date {entry.date} produced {len(added)} new entries"
            )
        result = self._read_after_write(
            lambda: self._hydrate_diary_entry(added[0]),
            operation=f"adding diary entry on date {entry.date}",
        )
        if not self._diary_entry_matches(result, entry, portion.portion_id):
            raise FatsecretWebVerificationError(
                "diary write did not match the requested item, amount, portion, meal, and date"
            )
        return result

    def delete_diary_entry(self, entry_id: int, date: int) -> WebDiaryEntryDeleteResult:
        """Delete one diary entry and verify absence; already absent is success."""

        entry_id = self._positive_id(entry_id, "entry_id")
        date = self._nonnegative_id(date, "date")
        before = self._get_diary_references(date)
        if not any(item.entry_id == entry_id for item in before):
            return WebDiaryEntryDeleteResult(
                entry_id=entry_id, date=date, deleted=False
            )
        delete_url = urljoin(
            self.BASE_URL,
            f"{self.DIARY_PATH}&action=deleteentry&eid={entry_id}&dt={date}",
        )
        self._get_authenticated(delete_url)
        after = self._read_after_write(
            lambda: self._get_diary_references(date),
            operation=f"deleting diary entry {entry_id}",
        )
        if any(item.entry_id == entry_id for item in after):
            raise FatsecretWebVerificationError(
                f"diary entry {entry_id} remained after deletion"
            )
        return WebDiaryEntryDeleteResult(entry_id=entry_id, date=date, deleted=True)

    def get_recipe(self, recipe_id: int) -> WebRecipeDetail:
        """Return fully hydrated metadata and ingredients for an owned recipe."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        summary = self._find_recipe_summary(recipe_id)
        edit_response, edit_page = self._get_recipe_edit(recipe_id)
        ingredients = []
        for row in edit_page.ingredient_rows:
            response = self._get_authenticated(row.edit_url)
            ingredients.append(
                parse_ingredient_detail(
                    response.text,
                    display_text=row.display_text,
                    nutrition_total=row.nutrition_total,
                )
            )
        metadata = edit_page.metadata
        return WebRecipeDetail(
            recipe_id=recipe_id,
            title=metadata.title,
            description=metadata.description,
            status=summary.status,
            nutrition_per_serving=summary.nutrition,
            preview_url=summary.preview_url,
            edit_url=edit_response.url,
            servings=metadata.servings,
            prep_minutes=metadata.prep_minutes,
            cook_minutes=metadata.cook_minutes,
            meal_types=metadata.meal_types,
            directions=metadata.directions,
            sharing=edit_page.sharing,
            ingredients=ingredients,
        )

    def create_recipe(self, recipe: WebRecipeWrite) -> WebRecipeDetail:
        """Create private recipe metadata and verify the assigned recipe."""

        recipe = WebRecipeWrite.model_validate(recipe)
        self._ensure_authenticated()
        create_url = self._recipe_edit_url(0) + "&action=save"
        response = self._post_mutation(
            create_url,
            data=recipe_form_payload(recipe),
            referer=self._recipe_edit_url(0),
            operation="creating recipe",
        )
        query = parse_qs(urlparse(response.url).query)
        values = query.get("recipeid", [])
        if not values or not values[0].isdigit() or values[0] == "0":
            raise FatsecretWebVerificationError(
                f"recipe create outcome is unknown; final URL was {response.url!r}"
            )
        created = self._read_after_write(
            lambda: self.get_recipe(int(values[0])), operation="creating recipe"
        )
        if not metadata_matches(created, recipe) or created.ingredients:
            raise FatsecretWebVerificationError(
                f"created recipe {created.recipe_id} did not match the requested metadata"
            )
        return created

    def replace_recipe(self, recipe_id: int, recipe: WebRecipeWrite) -> WebRecipeDetail:
        """Replace recipe metadata while preserving ingredients and sharing state."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        recipe = WebRecipeWrite.model_validate(recipe)
        _, before = self._get_recipe_edit(recipe_id)
        before_ids = [row.entry_id for row in before.ingredient_rows]
        target_url = self._recipe_edit_url(recipe_id) + "&action=save"
        self._post_mutation(
            target_url,
            data=recipe_form_payload(recipe, sharing=before.sharing),
            referer=self._recipe_edit_url(recipe_id),
            operation=f"replacing recipe {recipe_id}",
        )
        current = self._read_after_write(
            lambda: self.get_recipe(recipe_id),
            operation=f"replacing recipe {recipe_id}",
        )
        if not metadata_matches(current, recipe):
            raise FatsecretWebVerificationError(
                f"recipe {recipe_id} replacement did not match the requested metadata"
            )
        if [ingredient.entry_id for ingredient in current.ingredients] != before_ids:
            raise FatsecretWebVerificationError(
                f"recipe {recipe_id} replacement unexpectedly changed ingredients"
            )
        return current

    def delete_recipe(self, recipe_id: int) -> WebRecipeDeleteResult:
        """Delete an owned recipe and verify it is absent; already absent is success."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        response = self._get_authenticated(self.cookbook_url)
        soup = BeautifulSoup(response.text, "lxml")
        row = self._cookbook_recipe_row(soup, recipe_id)
        if row is None:
            return WebRecipeDeleteResult(recipe_id=recipe_id, deleted=False)

        target = self._delete_postback_target(row, recipe_id)
        payload = {
            **self._hidden_fields(soup),
            "__EVENTTARGET": target,
            "__EVENTARGUMENT": "",
        }
        self._post_mutation(
            self.cookbook_url,
            data=payload,
            referer=self.cookbook_url,
            operation=f"deleting recipe {recipe_id}",
        )
        remaining = self._read_after_write(
            self.list_recipes, operation=f"deleting recipe {recipe_id}"
        )
        if any(recipe.recipe_id == recipe_id for recipe in remaining):
            raise FatsecretWebVerificationError(
                f"recipe {recipe_id} remained in the cookbook after deletion"
            )
        return WebRecipeDeleteResult(recipe_id=recipe_id, deleted=True)

    def list_food_portions(self, recipe_id: int, food_id: int) -> WebFoodPortions:
        """Resolve portion IDs directly for a known food ID in a recipe."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        food_id = self._positive_id(food_id, "food_id")
        self._find_recipe_summary(recipe_id)
        return self._resolve_food_portions(recipe_id, food_id)

    def _resolve_food_portions(self, recipe_id: int, food_id: int) -> WebFoodPortions:
        url = urljoin(self.BASE_URL, self.PORTION_OPTIONS_PATH)
        params = {"rid": food_id, "prid": recipe_id, "exp": ""}
        self._ensure_authenticated()
        response = self._get(url, params=params)
        if self._looks_like_login(response.text):
            self._authenticated = False
            self.login()
            response = self._get(url, params=params)
            if self._looks_like_login(response.text):
                raise FatsecretWebAuthenticationError(
                    "FatSecret member session expired while resolving food portions"
                )
        return parse_food_portions(response.text, food_id=food_id)

    def add_recipe_ingredient(
        self, recipe_id: int, ingredient: WebIngredientWrite
    ) -> WebRecipeIngredient:
        """Add one known food ID and verify exactly one new ingredient row."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        ingredient = WebIngredientWrite.model_validate(ingredient)
        _, before = self._get_recipe_edit(recipe_id)
        portions = self._resolve_food_portions(recipe_id, ingredient.food_id)
        portion = self._select_portion(portions, ingredient.portion_id)
        self._require_whole_grams(ingredient.amount, portion.is_grams)
        before_ids = {row.entry_id for row in before.ingredient_rows}
        target_url = urljoin(
            self.BASE_URL,
            f"/Diary.aspx?pa=mrece&action=addentry&recipeid={recipe_id}",
        )
        self._post_mutation(
            target_url,
            data={
                "entryname": portions.food_name,
                "portionamount": format(ingredient.amount, "f"),
                "portionid": str(portion.portion_id),
                "recipeid": str(ingredient.food_id),
                "asrecipeid": str(ingredient.food_id),
            },
            referer=self._recipe_edit_url(recipe_id),
            operation=f"adding ingredient to recipe {recipe_id}",
        )
        _, after = self._read_after_write(
            lambda: self._get_recipe_edit(recipe_id),
            operation=f"adding ingredient to recipe {recipe_id}",
        )
        new_rows = [
            row for row in after.ingredient_rows if row.entry_id not in before_ids
        ]
        if len(new_rows) != 1:
            raise FatsecretWebVerificationError(
                f"ingredient add to recipe {recipe_id} produced {len(new_rows)} new rows"
            )
        added = self._read_after_write(
            lambda: self._hydrate_ingredient(new_rows[0]),
            operation=f"adding ingredient to recipe {recipe_id}",
        )
        self._verify_ingredient(added, ingredient, portion.portion_id)
        return added

    def replace_recipe_ingredient(
        self,
        recipe_id: int,
        entry_id: int,
        ingredient: WebIngredientWrite,
    ) -> WebRecipeIngredient:
        """Replace one ingredient and verify its food, portion, and quantity."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        entry_id = self._positive_id(entry_id, "entry_id")
        ingredient = WebIngredientWrite.model_validate(ingredient)
        _, edit_page = self._get_recipe_edit(recipe_id)
        row = next(
            (row for row in edit_page.ingredient_rows if row.entry_id == entry_id), None
        )
        if row is None:
            raise FatsecretWebNotFoundError(
                f"ingredient {entry_id} is not in recipe {recipe_id}"
            )
        portions = self._resolve_food_portions(recipe_id, ingredient.food_id)
        portion = self._select_portion(portions, ingredient.portion_id)
        self._require_whole_grams(ingredient.amount, portion.is_grams)
        target_url = urljoin(
            self.BASE_URL,
            "/Diary.aspx?pa=fjrd"
            f"&rid={ingredient.food_id}&prid={recipe_id}&iid={entry_id}",
        )
        self._post_mutation(
            target_url,
            data={
                "entryname": portions.food_name,
                "portionamount": format(ingredient.amount, "f"),
                "portionid": str(portion.portion_id),
                "action": "Save",
            },
            referer=row.edit_url,
            operation=f"replacing ingredient {entry_id}",
        )
        _, current_page = self._read_after_write(
            lambda: self._get_recipe_edit(recipe_id),
            operation=f"replacing ingredient {entry_id}",
        )
        current_row = next(
            (row for row in current_page.ingredient_rows if row.entry_id == entry_id),
            None,
        )
        if current_row is None:
            raise FatsecretWebVerificationError(
                f"ingredient {entry_id} disappeared while replacing it"
            )
        current = self._read_after_write(
            lambda: self._hydrate_ingredient(current_row),
            operation=f"replacing ingredient {entry_id}",
        )
        self._verify_ingredient(current, ingredient, portion.portion_id)
        return current

    def delete_recipe_ingredient(self, recipe_id: int, entry_id: int) -> bool:
        """Delete an ingredient and verify absence; already absent is success."""

        recipe_id = self._positive_id(recipe_id, "recipe_id")
        entry_id = self._positive_id(entry_id, "entry_id")
        _, before = self._get_recipe_edit(recipe_id)
        if not any(row.entry_id == entry_id for row in before.ingredient_rows):
            return False
        delete_url = urljoin(
            self.BASE_URL,
            "/Diary.aspx?pa=mrece&action=deleteentry"
            f"&iid={entry_id}&recipeid={recipe_id}",
        )
        response = self._get_authenticated(delete_url)
        if f"recipeid={recipe_id}" not in response.url:
            raise FatsecretWebVerificationError(
                f"ingredient {entry_id} delete outcome is unknown"
            )
        _, after = self._read_after_write(
            lambda: self._get_recipe_edit(recipe_id),
            operation=f"deleting ingredient {entry_id}",
        )
        if any(row.entry_id == entry_id for row in after.ingredient_rows):
            raise FatsecretWebVerificationError(
                f"ingredient {entry_id} remained after deletion"
            )
        return True

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
        calculated_response = self._post_mutation(
            self.rdi_settings_url,
            data=calculate_payload,
            referer=self.rdi_settings_url,
            operation="calculating RDI",
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
        save_response = self._post_mutation(
            self.rdi_settings_url,
            data=save_payload,
            referer=self.rdi_settings_url,
            operation="saving RDI",
        )
        if "Diary.aspx" not in save_response.url:
            raise FatsecretWebVerificationError(
                "FatSecret RDI save did not return to the diary; outcome is unknown"
            )

        current = self._read_after_write(self.get_rdi, operation="saving RDI")
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

    def _get_authenticated(
        self, url: str, *, params: dict[str, int | str] | None = None
    ) -> requests.Response:
        if not self._authenticated:
            self.login()
        response = self._get(url, params=params)
        if self._is_authenticated(response.text):
            return response

        self._authenticated = False
        self.login()
        response = self._get(url, params=params)
        if not self._is_authenticated(response.text):
            raise FatsecretWebAuthenticationError(
                "FatSecret member session expired during page retrieval"
            )
        return response

    def _get(
        self, url: str, *, params: dict[str, int | str] | None = None
    ) -> requests.Response:
        """Perform a safe GET using the configured transient retry policy."""

        def request() -> requests.Response:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response

        try:
            return self._retries(request) if self._retries is not None else request()
        except requests.HTTPError as error:
            if error.response is not None:
                self._raise_for_status(error.response)
            raise

    def _ensure_authenticated(self) -> None:
        if not self._authenticated:
            self.login()

    def _post_mutation(
        self,
        url: str,
        *,
        data: dict[str, str],
        referer: str,
        operation: str,
    ) -> requests.Response:
        """Post a mutation, honoring explicit rate limits between attempts."""

        self._ensure_authenticated()
        while True:
            try:
                response = self._session.post(
                    url,
                    data=data,
                    headers={
                        "Origin": self.BASE_URL,
                        "Referer": referer,
                    },
                    timeout=self._timeout,
                )
            except (requests.Timeout, requests.ConnectionError) as error:
                raise FatsecretWebVerificationError(
                    f"FatSecret connection failed while {operation}; outcome is unknown"
                ) from error
            try:
                self._raise_for_status(response)
            except FatsecretWebRateLimitError as error:
                if not self._wait_on_rate_limit:
                    raise
                delay = (
                    error.retry_after
                    if error.retry_after is not None
                    else self._default_retry_after
                )
                time.sleep(delay)
                continue
            break
        if not self._is_authenticated(response.text):
            self._authenticated = False
            raise FatsecretWebVerificationError(
                f"FatSecret session expired while {operation}; outcome is unknown"
            )
        return response

    @staticmethod
    def _read_after_write(callback, *, operation: str):
        """Map post-write read failures to an explicitly ambiguous outcome."""

        try:
            return callback()
        except FatsecretWebRateLimitError as error:
            raise FatsecretWebVerificationError(
                f"FatSecret rate-limited verification after {operation}; outcome is unknown",
                retry_after=error.retry_after,
            ) from error
        except requests.RequestException as error:
            raise FatsecretWebVerificationError(
                f"FatSecret verification failed after {operation}; outcome is unknown"
            ) from error

    def _find_recipe_summary(self, recipe_id: int) -> WebRecipeSummary:
        for recipe in self.list_recipes():
            if recipe.recipe_id == recipe_id:
                return recipe
        raise FatsecretWebNotFoundError(f"member recipe {recipe_id} was not found")

    def _get_recipe_edit(
        self, recipe_id: int
    ) -> tuple[requests.Response, RecipeEditPage]:
        response = self._get_authenticated(self._recipe_edit_url(recipe_id))
        try:
            parsed = parse_recipe_edit_page(response.text, base_url=response.url)
        except FatsecretWebParseError as error:
            if not any(recipe.recipe_id == recipe_id for recipe in self.list_recipes()):
                raise FatsecretWebNotFoundError(
                    f"member recipe {recipe_id} was not found"
                ) from error
            raise
        return response, parsed

    def _hydrate_ingredient(self, row: object) -> WebRecipeIngredient:
        response = self._get_authenticated(getattr(row, "edit_url"))
        return parse_ingredient_detail(
            response.text,
            display_text=getattr(row, "display_text"),
            nutrition_total=getattr(row, "nutrition_total"),
        )

    def _get_diary_references(self, date: int) -> list[DiaryEntryReference]:
        response = self._get_authenticated(self._diary_date_url(date))
        return parse_diary_entry_references(
            response.text, base_url=response.url, expected_date=date
        )

    def _hydrate_diary_entry(self, reference: DiaryEntryReference) -> WebDiaryEntry:
        response = self._get_authenticated(reference.edit_url)
        result = parse_diary_entry(response.text, edit_url=response.url)
        if result.entry_id != reference.entry_id or result.date != reference.date:
            raise FatsecretWebVerificationError(
                f"diary entry {reference.entry_id} detail did not match its index link"
            )
        return result

    @staticmethod
    def _select_portion(portions: WebFoodPortions, portion_id: int | None):
        if portion_id is not None:
            selected = next(
                (
                    portion
                    for portion in portions.portions
                    if portion.portion_id == portion_id
                ),
                None,
            )
            if selected is None:
                raise ValueError(
                    f"portion_id {portion_id} is not valid for food {portions.food_id}"
                )
            return selected
        grams = next(
            (portion for portion in portions.portions if portion.is_grams), None
        )
        if grams is None:
            raise ValueError(f"food {portions.food_id} has no grams portion")
        return grams

    @staticmethod
    def _select_diary_portion(
        portions: WebDiaryItemPortions, portion_id: int | None
    ) -> WebDiaryPortion:
        if portion_id is not None:
            selected = next(
                (item for item in portions.portions if item.portion_id == portion_id),
                None,
            )
            if selected is None:
                raise ValueError(
                    f"portion_id {portion_id} is not valid for diary item {portions.item_id}"
                )
            return selected
        grams = next((item for item in portions.portions if item.is_grams), None)
        if grams is not None:
            return grams
        if len(portions.portions) == 1:
            return portions.portions[0]
        raise ValueError(
            f"diary item {portions.item_id} requires an explicit portion_id"
        )

    @staticmethod
    def _require_supported_diary_amount(
        amount: Decimal, portion: WebDiaryPortion
    ) -> None:
        FatsecretWebClient._require_whole_grams(amount, portion.is_grams)

    @staticmethod
    def _require_whole_grams(amount: Decimal, is_grams: bool) -> None:
        if is_grams and amount != amount.to_integral_value():
            raise ValueError(
                "FatSecret member website stores gram portions as whole numbers"
            )

    @staticmethod
    def _diary_entry_matches(
        actual: WebDiaryEntry, requested: WebDiaryEntryWrite, portion_id: int
    ) -> bool:
        return all(
            (
                actual.item_id == requested.item_id,
                actual.entry_name == requested.entry_name,
                actual.amount == requested.amount,
                actual.portion_id == portion_id,
                actual.meal == requested.meal,
                actual.date == requested.date,
            )
        )

    @staticmethod
    def _verify_ingredient(
        actual: WebRecipeIngredient,
        requested: WebIngredientWrite,
        portion_id: int,
    ) -> None:
        if (
            actual.food_id != requested.food_id
            or actual.amount != requested.amount
            or actual.portion_id != portion_id
        ):
            raise FatsecretWebVerificationError(
                "ingredient write did not match the requested food, amount, and portion"
            )

    def _recipe_edit_url(self, recipe_id: int) -> str:
        return urljoin(self.BASE_URL, self.RECIPE_EDIT_PATH.format(recipe_id=recipe_id))

    def _diary_date_url(self, date: int) -> str:
        return urljoin(self.BASE_URL, f"{self.DIARY_PATH}&dt={date}")

    def _diary_item_url(self, item_id: int, date: int) -> str:
        return urljoin(
            self.BASE_URL,
            f"{self.DIARY_ENTRY_PATH}&rid={item_id}&dt={date}",
        )

    @classmethod
    def _cookbook_recipe_row(cls, soup: BeautifulSoup, recipe_id: int) -> Tag | None:
        for row in soup.select("td.borderBottom"):
            link = row.select_one('a[href*="Diary.aspx?pa=mrece"][href*="recipeid="]')
            if link is not None and cls._recipe_id_from_edit_link(link) == recipe_id:
                return row
        return None

    @classmethod
    def _delete_postback_target(cls, row: Tag, recipe_id: int) -> str:
        for link in row.select("a"):
            marker = " ".join(
                (
                    link.get_text(" ", strip=True),
                    str(link.get("title", "")),
                    str(link.get("href", "")),
                    str(link.get("onclick", "")),
                    " ".join(str(image.get("src", "")) for image in link.select("img")),
                )
            )
            if "delete" not in marker.casefold():
                continue
            match = cls._POSTBACK_RE.search(marker)
            if match:
                return match.group("target")
        raise FatsecretWebParseError(
            f"cookbook row for recipe {recipe_id} has no delete postback"
        )

    @staticmethod
    def _positive_id(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value <= 0:
            raise ValueError(f"{name} must be greater than zero")
        return value

    @staticmethod
    def _nonnegative_id(value: int, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an integer")
        if value < 0:
            raise ValueError(f"{name} must not be negative")
        return value

    @staticmethod
    def _looks_like_login(html: str) -> bool:
        return (
            BeautifulSoup(html, "lxml").select_one('input[name$="Logincontrol1$Name"]')
            is not None
        )

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 429:
            parsed = parse_retry_after(response.headers.get("Retry-After"))
            retry_after = int(parsed) if parsed is not None else None
            raise FatsecretWebRateLimitError(
                "FatSecret rate limit exceeded", retry_after=retry_after
            )
        response.raise_for_status()

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
