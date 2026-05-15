API Documentation
=================

As of v1.0 every endpoint method carries an explicit ``_vN`` suffix matching
the upstream API version (e.g. ``foods_search_v5``, ``food_get_v5``,
``recipes_search_v3``). The unsuffixed legacy names (``foods_search``,
``food_get``, ...) remain available as **deprecated aliases** for the v1.x
line and emit :class:`DeprecationWarning` when called. To surface those
warnings during development, run Python with::

    python -W default::DeprecationWarning:fatsecret

The endpoint methods below are exposed via resource sub-objects on a
:class:`fatsecret.Fatsecret` instance -- e.g. ``fs.foods.search_v5(...)`` --
with one section per Python resource class (the actual import path you
use). Client-only helpers (auth handshake, session lifecycle, time
conversion) are listed at the bottom under **Client utilities**.

FoodsResource
-------------

.. autoclass:: fatsecret.resources.foods.FoodsResource
   :members:

ClassificationResource
----------------------

.. autoclass:: fatsecret.resources.classification.ClassificationResource
   :members:

RecipesResource
---------------

.. autoclass:: fatsecret.resources.recipes.RecipesResource
   :members:

ProfileFoodsResource
--------------------

.. autoclass:: fatsecret.resources.profile_foods.ProfileFoodsResource
   :members:

DiaryResource
-------------

.. autoclass:: fatsecret.resources.diary.DiaryResource
   :members:

ExercisesResource
-----------------

.. autoclass:: fatsecret.resources.exercises.ExercisesResource
   :members:

WeightResource
--------------

.. autoclass:: fatsecret.resources.weight.WeightResource
   :members:

ProfileResource
---------------

.. autoclass:: fatsecret.resources.profile.ProfileResource
   :members:

MealsResource
-------------

.. autoclass:: fatsecret.resources.meals.MealsResource
   :members:

NativeResource
--------------

.. autoclass:: fatsecret.resources.native.NativeResource
   :members:

FeedbackResource
----------------

.. autoclass:: fatsecret.resources.feedback.FeedbackResource
   :members:

Client utilities
----------------

.. automethod:: fatsecret.Fatsecret.authenticate

.. automethod:: fatsecret.Fatsecret.close

.. automethod:: fatsecret.Fatsecret.fatsecret_authenticate

.. automethod:: fatsecret.Fatsecret.get_authorize_url

.. automethod:: fatsecret.Fatsecret.unix_time

.. automethod:: fatsecret.Fatsecret.valid_response

Models
------

v3 typed response models. Returned by the methods above; access fields via
attribute access (``food.food_id`` not ``food["food_id"]``). All inherit from
``_FS_Base`` which sets ``extra="allow"`` and provides ``.to_dict()`` for the
v2 dict shape.

Foods
~~~~~

.. autopydantic_model:: fatsecret.models.Food
.. autopydantic_model:: fatsecret.models.Foods
.. autopydantic_model:: fatsecret.models.FoodsSearch
.. autopydantic_model:: fatsecret.models.FoodResults
.. autopydantic_model:: fatsecret.models.FoodSubCategories
.. autopydantic_model:: fatsecret.models.FoodAttributes
.. autopydantic_model:: fatsecret.models.FoodImage
.. autopydantic_model:: fatsecret.models.FoodImages
.. autopydantic_model:: fatsecret.models.Serving
.. autopydantic_model:: fatsecret.models.Allergen
.. autopydantic_model:: fatsecret.models.Allergens
.. autopydantic_model:: fatsecret.models.Preference
.. autopydantic_model:: fatsecret.models.Preferences

Recipes
~~~~~~~

.. autopydantic_model:: fatsecret.models.Recipe
.. autopydantic_model:: fatsecret.models.Recipes
.. autopydantic_model:: fatsecret.models.RecipesRecipeRecipeIngredients
.. autopydantic_model:: fatsecret.models.RecipesRecipeRecipeNutrition
.. autopydantic_model:: fatsecret.models.RecipesRecipeRecipeTypes

Diary
~~~~~

Food diary entries (per-day / per-month nutrition logs).

.. autopydantic_model:: fatsecret.models.Day
.. autopydantic_model:: fatsecret.models.Month
.. autopydantic_model:: fatsecret.models.FoodEntry
.. autopydantic_model:: fatsecret.models.FoodEntries

Profile
~~~~~~~

.. autopydantic_model:: fatsecret.models.Profile

Exercises
~~~~~~~~~

.. autopydantic_model:: fatsecret.models.Exercise
.. autopydantic_model:: fatsecret.models.ExerciseEntry
.. autopydantic_model:: fatsecret.models.ExerciseEntries
.. autopydantic_model:: fatsecret.models.ExerciseTypes
.. autopydantic_model:: fatsecret.models.ExerciseDay
.. autopydantic_model:: fatsecret.models.ExerciseMonth

Weight
~~~~~~

.. autopydantic_model:: fatsecret.models.WeightDay
.. autopydantic_model:: fatsecret.models.WeightMonth
