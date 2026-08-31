"""Parsers and form encoders for FatSecret member recipe pages."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from .errors import FatsecretWebParseError
from .models import (
    WebFoodPortion,
    WebFoodPortions,
    WebMealType,
    WebNutrition,
    WebRecipeIngredient,
    WebRecipeWrite,
)

MEAL_TYPE_BY_ID = {
    1: WebMealType.APPETIZERS,
    2: WebMealType.SOUPS,
    3: WebMealType.MAIN_DISHES,
    4: WebMealType.SIDE_DISHES,
    5: WebMealType.BREADS_AND_BAKED_PRODUCTS,
    6: WebMealType.SALADS_AND_SALAD_DRESSINGS,
    7: WebMealType.SAUCES_AND_CONDIMENTS,
    8: WebMealType.DESSERTS,
    9: WebMealType.SNACKS,
    10: WebMealType.BEVERAGES,
    11: WebMealType.OTHER,
    12: WebMealType.BREAKFAST,
    13: WebMealType.LUNCH,
}
MEAL_TYPE_ID = {meal_type: type_id for type_id, meal_type in MEAL_TYPE_BY_ID.items()}


@dataclass(frozen=True)
class RecipeIngredientRow:
    entry_id: int
    display_text: str
    edit_url: str
    nutrition_total: WebNutrition


@dataclass(frozen=True)
class RecipeEditPage:
    metadata: WebRecipeWrite
    sharing: bool
    ingredient_rows: list[RecipeIngredientRow]


def _required_value(soup: BeautifulSoup | Tag, selector: str) -> str:
    element = soup.select_one(selector)
    if element is None:
        raise FatsecretWebParseError(f"recipe form is missing {selector}")
    if element.name == "textarea":
        return element.get_text().strip()
    value = element.get("value")
    if value is None:
        raise FatsecretWebParseError(f"recipe form field {selector} has no value")
    return str(value).strip()


def _decimal(value: str, *, field: str, allow_missing: bool = False) -> Decimal | None:
    normalized = value.strip().replace(",", "")
    if allow_missing and normalized in {"", "-"}:
        return None
    try:
        parts = normalized.split()
        if len(parts) in {1, 2} and "/" in parts[-1]:
            numerator, denominator = parts[-1].split("/", 1)
            fraction = Decimal(numerator) / Decimal(denominator)
            return (Decimal(parts[0]) + fraction) if len(parts) == 2 else fraction
        return Decimal(normalized)
    except (DecimalException, ValueError) as error:
        raise FatsecretWebParseError(f"invalid {field}: {value!r}") from error


def _integer(value: str, *, field: str) -> int:
    try:
        return int(value.strip())
    except ValueError as error:
        raise FatsecretWebParseError(f"invalid {field}: {value!r}") from error


def parse_recipe_edit_page(html: str, *, base_url: str) -> RecipeEditPage:
    """Parse writable metadata and ingredient row summaries from an edit page."""

    soup = BeautifulSoup(html, "lxml")
    metadata_form = soup.select_one("#dtform")
    if metadata_form is None:
        raise FatsecretWebParseError("recipe edit page has no metadata form")

    meal_types = [
        meal_type
        for type_id, meal_type in MEAL_TYPE_BY_ID.items()
        if soup.select_one(f'input[name="{type_id}_type"][checked]') is not None
    ]
    directions = []
    for index in range(1, 9):
        step = soup.select_one(f'textarea[name="step{index}"]')
        if step is not None and step.get_text().strip():
            directions.append(step.get_text().strip())

    metadata = WebRecipeWrite(
        title=_required_value(metadata_form, '[name="title"]'),
        description=_required_value(metadata_form, '[name="description"]'),
        servings=_decimal(
            _required_value(metadata_form, '[name="portions"]'), field="servings"
        ),
        prep_minutes=_integer(
            _required_value(metadata_form, '[name="prepTime"]'), field="prep time"
        ),
        cook_minutes=_integer(
            _required_value(metadata_form, '[name="cookTime"]'), field="cook time"
        ),
        meal_types=meal_types,
        directions=directions,
    )

    rows: list[RecipeIngredientRow] = []
    seen_ids: set[int] = set()
    for link in soup.select('a[href*="pa=fjrd"][href*="iid="]'):
        query = parse_qs(urlparse(str(link.get("href", ""))).query)
        values = query.get("iid", [])
        if not values or not values[0].isdigit():
            raise FatsecretWebParseError("ingredient edit link has no numeric iid")
        entry_id = int(values[0])
        if entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)

        table_row = link.find_parent("tr")
        nutrient_cells = table_row.select("td.greyback") if table_row else []
        if len(nutrient_cells) != 6:
            raise FatsecretWebParseError(
                f"ingredient {entry_id} row has {len(nutrient_cells)} nutrition cells"
            )
        values = [cell.get_text(" ", strip=True) for cell in nutrient_cells]
        rows.append(
            RecipeIngredientRow(
                entry_id=entry_id,
                display_text=link.get_text(" ", strip=True),
                edit_url=urljoin(base_url, str(link.get("href", ""))),
                nutrition_total=WebNutrition(
                    fat_g=_decimal(
                        values[0], field="ingredient fat", allow_missing=True
                    ),
                    carbohydrate_g=_decimal(
                        values[1], field="ingredient carbohydrate", allow_missing=True
                    ),
                    fiber_g=_decimal(
                        values[2], field="ingredient fiber", allow_missing=True
                    ),
                    sugar_g=_decimal(
                        values[3], field="ingredient sugar", allow_missing=True
                    ),
                    protein_g=_decimal(
                        values[4], field="ingredient protein", allow_missing=True
                    ),
                    calories=_decimal(
                        values[5], field="ingredient calories", allow_missing=True
                    ),
                ),
            )
        )

    return RecipeEditPage(
        metadata=metadata,
        sharing=soup.select_one('input[name="osharing"][checked]') is not None,
        ingredient_rows=rows,
    )


def parse_ingredient_detail(
    html: str,
    *,
    display_text: str,
    nutrition_total: WebNutrition,
) -> WebRecipeIngredient:
    """Hydrate IDs and quantity from an ingredient edit page."""

    soup = BeautifulSoup(html, "lxml")
    form = soup.select_one("#updateFormOther")
    if form is None:
        raise FatsecretWebParseError("ingredient edit page has no update form")
    action = str(form.get("action", ""))
    query = parse_qs(urlparse(action).query)

    def numeric_query(name: str) -> int:
        values = query.get(name, [])
        if not values or not values[0].isdigit():
            raise FatsecretWebParseError(
                f"ingredient update form has no numeric {name}"
            )
        return int(values[0])

    selected = form.select_one('select[name="portionid"] option[selected]')
    raw_portion_id = str(selected.get("value", "")) if selected else ""
    if (
        selected is None
        or not raw_portion_id.lstrip("-").isdigit()
        or int(raw_portion_id) == 0
    ):
        raise FatsecretWebParseError("ingredient update form has no selected portion")
    return WebRecipeIngredient(
        entry_id=numeric_query("iid"),
        food_id=numeric_query("rid"),
        name=_required_value(form, '[name="entryname"]'),
        amount=_decimal(
            _required_value(form, '[name="portionamount"]'), field="ingredient amount"
        ),
        portion_id=int(raw_portion_id),
        portion_name=selected.get_text(" ", strip=True),
        display_text=display_text,
        nutrition_total=nutrition_total,
    )


def parse_food_portions(html: str, *, food_id: int) -> WebFoodPortions:
    """Parse the member-site portion-options fragment for a known food ID."""

    soup = BeautifulSoup(html, "lxml")
    name = _required_value(soup, '[name="entryname"]')
    options = []
    for option in soup.select('select[name="portionid"] option[value]'):
        raw_id = str(option.get("value", ""))
        if not raw_id.lstrip("-").isdigit() or int(raw_id) == 0:
            raise FatsecretWebParseError(f"food {food_id} has a non-numeric portion ID")
        label = option.get_text(" ", strip=True)
        options.append(
            WebFoodPortion(
                portion_id=int(raw_id),
                label=label,
                is_grams=label.casefold() in {"g", "gram", "grams"},
            )
        )
    if not options:
        raise FatsecretWebParseError(f"food {food_id} returned no portion choices")
    return WebFoodPortions(food_id=food_id, food_name=name, portions=options)


def recipe_form_payload(
    recipe: WebRecipeWrite, *, sharing: bool = False
) -> dict[str, str]:
    """Encode the complete member recipe metadata form."""

    payload = {
        "title": recipe.title,
        "description": recipe.description,
        "portions": format(recipe.servings, "f"),
        "prepTime": str(recipe.prep_minutes),
        "cookTime": str(recipe.cook_minutes),
        "sharing": "",
        "osharing": str(sharing).lower(),
    }
    for meal_type in recipe.meal_types:
        type_id = MEAL_TYPE_ID[meal_type]
        payload[f"{type_id}_type"] = str(type_id)
    for index in range(1, 9):
        payload[f"step{index}"] = (
            recipe.directions[index - 1] if index <= len(recipe.directions) else ""
        )
    return payload


def metadata_matches(detail: object, requested: WebRecipeWrite) -> bool:
    """Compare canonical writable fields without rendered-text formatting."""

    return all(
        (
            getattr(detail, "title") == requested.title,
            getattr(detail, "description") == requested.description,
            getattr(detail, "servings") == requested.servings,
            getattr(detail, "prep_minutes") == requested.prep_minutes,
            getattr(detail, "cook_minutes") == requested.cook_minutes,
            getattr(detail, "meal_types") == requested.meal_types,
            getattr(detail, "directions") == requested.directions,
        )
    )


__all__ = [
    "RecipeEditPage",
    "RecipeIngredientRow",
    "metadata_matches",
    "parse_food_portions",
    "parse_ingredient_detail",
    "parse_recipe_edit_page",
    "recipe_form_payload",
]
