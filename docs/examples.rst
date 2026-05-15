.. _examples:

Usage examples
==============

Short, runnable recipes for the most common workflows on the v3
namespaced surface (``fs.foods``, ``fs.diary``, ``fs.recipes`` ...).
Methods return typed `Pydantic <https://docs.pydantic.dev/>`_ models, so
prefer attribute access (``food.food_name``) over dict lookups.

All numeric nutrition fields (``calories``, ``protein``, ``fat`` ...) are
``decimal.Decimal`` to preserve API precision — convert with ``float()``
when you need to do arithmetic with regular numbers.

.. contents::
    :local:
    :depth: 1


Initialize a public client (OAuth2)
-----------------------------------

For public-data endpoints (food search, food.get, recipe search, ...)
the client-credentials flow is enough. No user login required.

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret(
        consumer_key="YOUR_KEY",
        consumer_secret="YOUR_SECRET",
        auth="oauth2",
        scopes=["basic"],
    )

    # Ready for any non-delegated call.
    foods = fs.foods.search_v5(search_expression="banana", max_results=3)


Initialize an authenticated client (OAuth1)
-------------------------------------------

For user-scoped endpoints (food diary, weight log, saved meals, ...)
use OAuth1 with a previously-obtained ``(token, secret)`` pair you have
persisted for the user.

.. code-block:: python

    from fatsecret import Fatsecret

    # token + secret were saved at the end of the OAuth1 dance
    # (see the "OAuth Examples" page for how to obtain them).
    access_token = ("USER_TOKEN", "USER_TOKEN_SECRET")

    fs = Fatsecret(
        consumer_key="YOUR_KEY",
        consumer_secret="YOUR_SECRET",
        session_token=access_token,
        auth="oauth1",
    )

    # User-scoped calls now work, e.g.:
    profile = fs.profile.get_v1()


Search foods
------------

``foods.search_v5`` returns ``list[Food]``. Iterate and read typed
attributes directly.

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret("KEY", "SECRET", auth="oauth2", scopes=["basic"])

    results = fs.foods.search_v5(search_expression="banana", max_results=5)

    for food in results:
        print(food.food_id, food.food_name, food.brand_name, food.food_type)
    # 38821 Banana None Generic
    # ...


Get nutrition for a specific food
---------------------------------

``foods.get_v5`` returns a single ``Food`` whose ``servings`` contain
per-serving nutrition. Each ``Serving`` carries ``Decimal`` macros.

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret("KEY", "SECRET", auth="oauth2", scopes=["basic"])

    food = fs.foods.get_v5(food_id=38821)

    print(food.food_name)
    for serving in food.servings.serving:
        print(
            serving.serving_description,
            f"{float(serving.calories):.0f} kcal",
            f"P {serving.protein}g  C {serving.carbohydrate}g  F {serving.fat}g",
        )


Search and log a meal
---------------------

Pick the first match for a query, then write a ``food_entry`` against
the user's diary. Requires an authenticated (OAuth1) client.

.. code-block:: python

    from datetime import date

    from fatsecret import Fatsecret

    fs = Fatsecret(
        "KEY", "SECRET",
        session_token=("USER_TOKEN", "USER_TOKEN_SECRET"),
        auth="oauth1",
    )

    # 1. Find the food.
    matches = fs.foods.search_v5(search_expression="banana", max_results=1)
    food = fs.foods.get_v5(food_id=matches[0].food_id)
    serving = food.servings.serving[0]

    # 2. Log one serving as breakfast for today.
    entries = fs.diary.entry_create_v1(
        food_id=food.food_id,
        food_entry_name=food.food_name,
        serving_id=serving.serving_id,
        number_of_units=1.0,
        meal="Breakfast",
        date=date.today(),
    )

    print("Logged entry id:", entries[0].food_entry_id)


Get the day's food entries
--------------------------

``diary.entries_get_v2`` returns ``list[FoodEntry]`` for a given day.
The ``date`` parameter accepts a ``date``/``datetime``/Unix timestamp —
the SDK converts it to FatSecret's day-since-epoch encoding for you.

.. code-block:: python

    from datetime import date

    from fatsecret import Fatsecret

    fs = Fatsecret(
        "KEY", "SECRET",
        session_token=("USER_TOKEN", "USER_TOKEN_SECRET"),
        auth="oauth1",
    )

    entries = fs.diary.entries_get_v2(date=date.today())

    total_kcal = sum(float(e.calories or 0) for e in entries)
    for e in entries:
        print(f"{e.meal:10s} {e.food_entry_name:30s} {e.calories} kcal")
    print(f"TOTAL: {total_kcal:.0f} kcal across {len(entries)} entries")


Recipe lookup with ingredients
------------------------------

``recipes.search_v3`` returns ``list[RecipesRecipe]``. The list view is
sparse — call ``recipes.get_v2`` for full ingredients and nutrition.

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret("KEY", "SECRET", auth="oauth2", scopes=["basic"])

    hits = fs.recipes.search_v3(
        search_expression="tomato soup",
        max_results=3,
    )
    for r in hits:
        print(r.recipe_id, r.recipe_name)

    # Drill into the first recipe for ingredients + macros.
    recipe = fs.recipes.get_v2(recipe_id=hits[0].recipe_id)
    print(recipe.recipe_name)
    for ingredient in recipe.recipe_ingredients.ingredient:
        print(" -", ingredient)
    print("kcal/serving:", recipe.recipe_nutrition.calories)


Backwards-compat dict access (``.to_dict()``)
---------------------------------------------

Callers migrating from v2 (which returned plain dicts) can drop into
the legacy shape via ``.to_dict()`` on any model. Useful as a
short-term shim while you port code to typed attribute access.

.. code-block:: python

    from pprint import pprint

    from fatsecret import Fatsecret

    fs = Fatsecret("KEY", "SECRET", auth="oauth2", scopes=["basic"])

    food = fs.foods.get_v5(food_id=38821)

    # Typed (preferred):
    print(food.food_name, food.food_id)

    # Dict (v2-compatible):
    pprint(food.to_dict())
    # {'food_id': '38821', 'food_name': 'Banana', 'servings': {...}, ...}
