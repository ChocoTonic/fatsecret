Migrating to v3
===============

What changed in v3
------------------

Methods on the namespaced ``Fatsecret`` surface (``fs.foods.*``,
``fs.recipes.*``, ``fs.diary.*``, ``fs.profile.*``, ``fs.weight.*``,
``fs.exercises.*``) that previously returned ``dict[str, Any]`` or
``list[dict[str, Any]]`` now return typed Pydantic v2 models —
``Food``, ``Recipe``, ``Profile``, ``FoodEntry``, ``ExerciseEntry``,
``Exercise``, ``Day`` and friends. The wire-level behavior is
unchanged; only the in-Python return shape is new. ``pydantic>=2.7``
is now a base dependency.

Quick fix for most callers
--------------------------

Replace square-bracket dict access with dotted attribute access:

.. code-block:: python

    # v2
    food["food_id"]
    food["food_name"]

    # v3
    food.food_id
    food.food_name

If you have a downstream consumer that genuinely needs the dict
shape (JSON serialization, a templating layer, an existing
``dict``-typed signature you can't change today) call ``.to_dict()``
on the model. That's the one-line escape hatch:

.. code-block:: python

    payload_for_legacy_consumer = food.to_dict()

``.to_dict()`` is ``model.model_dump(mode="json")`` under the hood, so
``Decimal`` values come back as JSON-safe strings — same shape your
v2 code was already handling off the wire.

Side-by-side examples
---------------------

Single food lookup
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    food = fs.foods.get_v1(food_id=12345)

    # v2
    food["food_name"]
    food["food_type"]
    food["servings"]["serving"][0]["calories"]

    # v3
    food.food_name                            # str
    food.food_type                            # Literal["Brand", "Generic"]
    food.servings.serving[0].calories         # Decimal

Food search
~~~~~~~~~~~

``search_v1`` returns a list of typed ``Food`` objects directly
(the wrapping ``foods``/``results`` envelope is unwrapped for you):

.. code-block:: python

    foods = fs.foods.search_v1(search_expression="banana")

    # v2
    for entry in foods:
        print(entry["food_id"], entry["food_name"])

    # v3
    for entry in foods:
        print(entry.food_id, entry.food_name)   # int, str

Diary entries
~~~~~~~~~~~~~

.. code-block:: python

    import datetime
    today = datetime.date.today()
    entries = fs.diary.entries_get_v2(date=today)   # list[FoodEntry]

    # v2
    for e in entries:
        print(e["meal"], e["calories"], e["protein"])

    # v3
    for e in entries:
        print(e.meal, e.calories, e.protein)
        # e.meal     -> Literal["Breakfast", "Lunch", "Dinner", "Other"]
        # e.calories -> Decimal (not float!)
        # e.protein  -> Decimal

Recipe lookup
~~~~~~~~~~~~~

.. code-block:: python

    recipe = fs.recipes.get_v1(recipe_id=88339)   # Recipe

    # v2
    recipe["recipe_name"]
    recipe["recipe_nutrition"]["calories"]

    # v3
    recipe.recipe_name                            # str
    recipe.recipe_nutrition.calories              # Decimal

(``Recipe`` is a friendly alias for the XSD-derived ``RecipesRecipe``
class. Either name imports the same model.)

User profile
~~~~~~~~~~~~

.. code-block:: python

    profile = fs.profile.get_v1()   # Profile

    # v2
    profile["last_weight_kg"]
    profile["weight_measure"]

    # v3
    profile.last_weight_kg                        # Optional[Decimal]
    profile.weight_measure                        # Optional[Literal["Kg", "Lb"]]

Resources that still return dict
--------------------------------

Four resource families intentionally kept their ``dict`` return
shape because the upstream XSD doesn't model them. Nothing changed
for callers of these:

- **Food Classification** (``fs.classification.*``) — brands,
  categories, sub-categories.
- **Saved Meals** (``fs.meals.*``) — saved meal CRUD and items.
- **Native APIs** (``fs.native.*``) — image recognition, NLP.
- **Feedback** (``fs.feedback.*``) — feedback submission.

If we get an XSD (or a stable enough HTML overlay) for any of these
in the future they'll be promoted to typed models in a minor
release. The dict shape is the migration path; we won't reshape it.

Mutators still return ``bool``
------------------------------

Methods that write rather than read return a plain success boolean,
not a model. No change from v2:

- ``fs.weight.update_v1(...)`` -> ``bool``
- ``fs.diary.entry_create_v1(...)`` -> ``list[FoodEntry]`` (the
  resulting entries, typed)
- ``fs.diary.entry_edit_v1(...)`` -> ``bool``
- ``fs.diary.entry_delete_v1(...)`` -> ``bool``
- ``fs.recipes.add_favorite_v1(...)`` -> ``bool``
- ``fs.recipes.delete_favorite_v1(...)`` -> ``bool``

Type details worth knowing
--------------------------

``Decimal`` for nutrition macros
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Calories, protein, carbs, fat, micronutrients — all ``Decimal``,
not ``float``. The XSD says ``xsd:decimal`` and we honor it because
floating-point rounding in nutrition math compounds quickly across a
day's worth of entries. Two consequences:

- Arithmetic between a ``Decimal`` and a ``float`` raises
  ``TypeError``. Use ``Decimal(str(my_float))`` to lift, or convert
  the model value with ``float(entry.calories)`` if you genuinely
  want lossy float math.
- ``json.dumps(model)`` won't work — ``Decimal`` isn't
  JSON-serializable by default. Use ``model.model_dump_json()`` or
  ``json.dumps(model.to_dict())`` (``to_dict`` already invokes
  ``model_dump(mode="json")`` which stringifies Decimals).

``Literal`` for closed enums
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Where the XSD declares an enum, the field is a ``Literal[...]`` —
the IDE autocompletes it and a typo lights up under mypy/pyright:

- ``Food.food_type`` -> ``Literal["Brand", "Generic"]``
- ``FoodEntry.meal`` -> ``Literal["Breakfast", "Lunch", "Dinner", "Other"]``
- ``Profile.weight_measure`` -> ``Optional[Literal["Kg", "Lb"]]``
- ``Profile.height_measure`` -> ``Optional[Literal["Cm", "Inch"]]``

``Ternary`` for FatSecret's tri-state booleans
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A handful of fields (``Allergen.value``, ``Preference.value``) use
FatSecret's quirky three-valued truthiness:

.. code-block:: python

    Ternary = Literal[-1, 0, 1, "Unknown", "True", "False"]

Both numeric and string forms are accepted because the upstream API
emits both depending on the endpoint version. Don't compare with
``is True`` / ``is False`` — use ``== "True"`` / ``== 1`` or, more
defensively, normalize via a small helper.

``extra="allow"`` — schema drift is non-fatal
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every model is configured with ``extra="allow"``. If FatSecret adds
a new field tomorrow that we haven't regenerated for, the model
preserves it (accessible via ``model.__pydantic_extra__``) instead of
rejecting the response. Drift is detected by CI's
``oas-regen-check``, not by runtime validation failures — your
production code keeps working.

The ``.to_dict()`` migration helper
-----------------------------------

Every model inherits a ``.to_dict()`` method that returns the v2
dict shape:

.. code-block:: python

    food = fs.foods.get_v1(food_id=12345)
    legacy_shape = food.to_dict()   # {"food_id": "12345", "food_name": "...", ...}

Use it as a per-call escape hatch when migrating a large codebase
incrementally. ``Decimal`` becomes a string (``mode="json"``),
matching what v2 callers were already getting off the wire.

Frequently broken patterns
--------------------------

Iterating like a dict
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # v2 — works on dicts
    for k, v in food.items():
        ...

    # v3 — Pydantic models aren't dicts
    for k, v in food.model_dump().items():
        ...

JSON-serializing a model
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # v2
    json.dumps(food)

    # v3 — pick one
    food.model_dump_json()              # returns a JSON string directly
    json.dumps(food.to_dict())          # round-trips through the dict shape

``.get()`` with a default
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # v2
    brand = food.get("brand_name", "Unknown")

    # v3 — use getattr or check Optional
    brand = food.brand_name or "Unknown"
    # or, if the field could be missing on a model with extra="allow":
    brand = getattr(food, "brand_name", None) or "Unknown"

Membership tests
~~~~~~~~~~~~~~~~

.. code-block:: python

    # v2
    if "brand_name" in food:
        ...

    # v3
    if food.brand_name is not None:
        ...

Why typed models?
-----------------

- **IDE autocompletion.** ``food.<TAB>`` lists every field with its
  type. No more guessing whether the key is ``food_name`` or
  ``foodName`` or ``name``.
- **Real types.** ``food.food_id`` is ``int``, not ``str``;
  ``serving.calories`` is ``Decimal``, not whatever the wire happened
  to send. Pydantic coerces both directions, so legacy fixtures that
  serialized integers as strings still validate.
- **Runtime validation catches schema drift.** When FatSecret changes
  an XSD-typed field's shape (rename, type change), validation fails
  loudly at the call site instead of silently propagating malformed
  data into your business logic.
- **Closed enums document themselves.** ``Literal["Brand", "Generic"]``
  is the spec — your type checker will tell you if you compare against
  the wrong string.
