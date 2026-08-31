"""Recipe edit and ingredient parser tests."""

from decimal import Decimal

from fatsecret.web.recipe_parser import (
    parse_food_portions,
    parse_ingredient_detail,
    parse_recipe_edit_page,
    recipe_form_payload,
)

EDIT_HTML = """
<html><body>Hello member | Sign out
<form id="dtform">
  <input name="title" value="Bean Stew">
  <textarea name="description">A filling stew.</textarea>
  <input name="portions" value="4">
  <input name="prepTime" value="10">
  <input name="cookTime" value="45">
  <input type="checkbox" name="3_type" value="3" checked>
  <input type="checkbox" name="13_type" value="13" checked>
</form>
<textarea name="step1">Mix ingredients.</textarea>
<textarea name="step2">Bake.</textarea>
<input type="checkbox" name="osharing" checked>
<table><tr><td class="borderBottom"><table><tr valign="top">
  <td><a title="edit" href="/Diary.aspx?pa=fjrd&amp;prid=11&amp;iid=22">15 g beans</a></td>
  <td class="greyback">1.50</td><td class="greyback">20</td>
  <td class="greyback">5</td><td class="greyback">2</td>
  <td class="greyback">7</td><td class="greyback">120</td>
</tr></table></td></tr></table>
</body></html>
"""

INGREDIENT_HTML = """
<form id="updateFormOther" action="/Diary.aspx?pa=fjrd&amp;rid=33&amp;prid=11&amp;iid=22">
  <input name="entryname" value="Beans">
  <input name="portionamount" value="15">
  <select name="portionid">
    <option value="44">cup</option>
    <option value="-1" selected>g</option>
  </select>
</form>
"""


def test_parse_recipe_edit_page_returns_metadata_and_rows():
    page = parse_recipe_edit_page(
        EDIT_HTML, base_url="https://foods.fatsecret.com/Diary.aspx"
    )

    assert page.metadata.title == "Bean Stew"
    assert page.metadata.servings == Decimal("4")
    assert [item.value for item in page.metadata.meal_types] == [
        "main_dishes",
        "lunch",
    ]
    assert page.metadata.directions == ["Mix ingredients.", "Bake."]
    assert page.sharing is True
    assert len(page.ingredient_rows) == 1
    assert page.ingredient_rows[0].nutrition_total.calories == Decimal("120")


def test_parse_ingredient_detail_hydrates_opaque_ids():
    row = parse_recipe_edit_page(
        EDIT_HTML, base_url="https://foods.fatsecret.com/Diary.aspx"
    ).ingredient_rows[0]

    ingredient = parse_ingredient_detail(
        INGREDIENT_HTML,
        display_text=row.display_text,
        nutrition_total=row.nutrition_total,
    )

    assert ingredient.entry_id == 22
    assert ingredient.food_id == 33
    assert ingredient.amount == Decimal("15")
    assert ingredient.portion_id == -1
    assert ingredient.portion_name == "g"


def test_parse_ingredient_detail_accepts_fatsecret_mixed_fraction_amount():
    row = parse_recipe_edit_page(
        EDIT_HTML, base_url="https://foods.fatsecret.com/Diary.aspx"
    ).ingredient_rows[0]
    html = INGREDIENT_HTML.replace('value="15"', 'value="7 7/8"')

    ingredient = parse_ingredient_detail(
        html,
        display_text="7 7/8 medium onions",
        nutrition_total=row.nutrition_total,
    )

    assert ingredient.amount == Decimal("7.875")


def test_parse_food_portions_marks_grams_without_assuming_its_id():
    portions = parse_food_portions(INGREDIENT_HTML, food_id=33)

    assert portions.food_name == "Beans"
    assert [(item.portion_id, item.is_grams) for item in portions.portions] == [
        (44, False),
        (-1, True),
    ]


def test_recipe_form_payload_is_complete_replacement():
    recipe = parse_recipe_edit_page(
        EDIT_HTML, base_url="https://foods.fatsecret.com/Diary.aspx"
    ).metadata

    payload = recipe_form_payload(recipe, sharing=True)

    assert payload["3_type"] == "3"
    assert payload["13_type"] == "13"
    assert payload["step1"] == "Mix ingredients."
    assert payload["step2"] == "Bake."
    assert payload["step8"] == ""
    assert payload["osharing"] == "true"
