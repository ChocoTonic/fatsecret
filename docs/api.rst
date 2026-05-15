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

.. Models section added by separate PR (docs/autodoc-pydantic-and-hide-generated).
