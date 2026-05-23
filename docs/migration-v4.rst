Migrating to v4
===============

What changed in v4
------------------

The HTTP verb sent by every diary-mutation method changed. v3 sent
``DELETE`` and ``PUT`` to FatSecret's method-style endpoint
(``/rest/server.api?method=...``); v4 sends ``POST`` to the same
endpoint. The wire-level params and the FatSecret-side semantics are
unchanged — only the HTTP verb is different.

Why the change
--------------

FatSecret's REST API exposes most endpoints two ways:

- A modern **path-based URL** (``/rest/food-entries/v1``) with a
  conventional HTTP verb (``DELETE`` for delete, ``PUT`` for edit).
- A legacy **method-param URL** (``/rest/server.api?method=...``) that
  accepts ``GET`` (reads) and ``POST`` (writes), and **rejects
  ``DELETE``/``PUT`` with HTTP 404**.

The auto-generated OAS scraper picked up the ``DELETE``/``PUT`` verb
that FatSecret's docs document for the path-based URL form, but the
generated client was routing all calls through the legacy method-param
URL. Result: every ``DELETE`` and ``PUT`` call in v3 silently failed
with 404, regardless of the operation succeeding semantically.

v4 maps ``DELETE``/``PUT`` down to ``POST`` for method-style
endpoints. ``GET`` (reads) and ``POST`` (writes that already used POST
in v3) are unchanged. The path-based native APIs (image recognition,
NLP, feedback) are not affected — they already use the correct REST
verbs against the modern URL.

Affected methods
----------------

All previously sent ``DELETE`` or ``PUT`` to the legacy URL and
silently 404'd. v4 sends ``POST``:

- ``fs.diary.entry_delete_v1``
- ``fs.diary.entry_edit_v1``
- ``fs.recipes.delete_favorite_v1`` (also affected; hand-written wrapper updated)
- ``fs.profile_foods.delete_v1``, ``fs.profile_foods.delete_favorite_v1``,
  ``fs.profile_foods.edit_v1``
- ``fs.meals.delete_v1``, ``fs.meals.edit_v1``,
  ``fs.meal_items.delete_v1``, ``fs.meal_items.edit_v1``
- ``fs.exercises.entries_update_v1``

The actual server-side semantics for each call are unchanged; only
the HTTP verb the client sends differs.

Migration steps
---------------

1. **Production code that calls these methods**: no changes needed.
   The Python API surface (``fs.diary.entry_delete_v1(food_entry_id=...)``)
   is identical. The only difference is what HTTP verb hits FatSecret,
   and v4's verb is the one the server actually accepts.

   A side-effect worth knowing: if you had v3 in production and your
   classifier-delete or entry-edit logic appeared to "almost work" —
   reads returned current state, but mutations seemed to be
   intermittently missed — v4 will start *actually* applying those
   mutations. Audit any consumer that built a workaround for the
   silent-fail behavior (e.g. duplicate-detection on re-read, or
   diary cleanup scripts that delete-by-iteration). Those workarounds
   become unnecessary; some may now over-fire.

2. **Test mocks that asserted the v3 verb**: update assertions from
   ``DELETE``/``PUT`` to ``POST``:

   .. code-block:: python

       # v3
       assert mock_call.call_args.kwargs["method"] == "DELETE"

       # v4
       assert mock_call.call_args.kwargs["method"] == "POST"

   This is the only test-suite-level change required.

3. **Local downstream workarounds**: if you implemented a workaround
   like ``fs._call({"method": "food_entry.delete", ...}, method="GET")``
   (because the v3 wrapper was 404-ing), you can drop the workaround
   and call ``fs.diary.entry_delete_v1(food_entry_id=...)`` directly.

Verification
------------

The lib's unit-test suite asserts the new verbs against fresh mocks;
running ``make test`` after pinning to ``fatsecret>=4.0.0`` is
sufficient to verify your downstream test mocks are updated.

To verify against live FatSecret:

.. code-block:: python

    from fatsecret import Fatsecret
    fs = Fatsecret(...)
    # Create a throwaway entry then delete it; v3 would 404 silently,
    # v4 returns FatSecret's success envelope.
    fs.diary.entry_create_v1(food_id=..., ...)
    entries = [e.to_dict() for e in fs.diary.entries_get_v2(...)]
    entry_id = entries[-1]["food_entry_id"]
    result = fs.diary.entry_delete_v1(food_entry_id=entry_id)
    # v3: silently returned None even though server returned 404
    # v4: returns True (success) or raises on real failure

No model/shape changes
----------------------

Unlike v3 — which introduced Pydantic v2 models on the namespaced
surface — v4 changes only the HTTP transport. All return types,
constructor signatures, and method names are identical. ``.to_dict()``
still works, attribute access still works, ``model_validate`` still
works. If your v3 code passes tests today and doesn't rely on the
broken v3 mutation behavior, it will run on v4 unmodified.
