Member Website API
==================

.. warning::

   This integration automates unsupported HTML forms on
   ``foods.fatsecret.com``. It is separate from the supported FatSecret
   Platform API and can break when the member website changes.

The member-web client supports account recipe CRUD and RDI operations that the
official API does not expose. Credentials remain in process memory and should
come from environment variables or an operating-system secret store.

Python client
-------------

.. code-block:: python

   from fatsecret import FatsecretWebClient, WebIngredientWrite, WebRecipeWrite

   with FatsecretWebClient(
       username,
       password,
       timeout=30,
       retries=True,
   ) as client:
       recipes = client.list_recipes()
       recipe = client.get_recipe(recipes[0].recipe_id)
       created = client.create_recipe(
           WebRecipeWrite(
               title="Bean Stew",
               description="A simple bean stew.",
               servings="4",
               prep_minutes=10,
               cook_minutes=45,
               meal_types=["main_dishes"],
               directions=["Combine ingredients.", "Cook until tender."],
           )
       )
       client.add_recipe_ingredient(
           created.recipe_id,
           WebIngredientWrite(food_id=35755, amount="100"),
       )

An omitted ``portion_id`` resolves the food-specific grams portion. Pass an
opaque nonzero ``portion_id`` returned by ``list_food_portions`` when an exact
non-grams serving is required. The client does not perform semantic food-name
searches. FatSecret uses ``-1`` as the grams portion for some foods, so callers
must not assume portion IDs are positive.

``timeout`` and ``retries`` have the same meaning as on the official
``Fatsecret`` client. Safe GET requests use the shared transient retry policy:
three attempts, with authoritative ``Retry-After`` delays and exponential
jitter when FatSecret does not provide a delay. Server-provided delays are not
capped by the 30-second network timeout. Pass ``retries=False`` to disable the
policy or a configured ``tenacity.Retrying`` instance to replace it. Login and
mutation POST requests are never retried automatically.

HTTP facade
-----------

Install the optional server dependencies::

   pip install "fatsecret[facade]"

Configure one member account and a separate facade bearer token::

   export FATSECRET_USERNAME=member-name
   export FATSECRET_PASSWORD=member-password
   export FATSECRET_FACADE_TOKEN=a-long-random-api-token
   export FATSECRET_FACADE_DB=/var/lib/fatsecret/member-facade.sqlite3
   fatsecret-member-api

FatSecret credentials are server-managed. Never include them in HTTP or MCP
request bodies. The facade binds to ``127.0.0.1:8000`` by default; place an
authenticated reverse proxy in front of it for remote access.

The manually maintained OpenAPI 3.1 contract is
``docs/api-spec/member-web.openapi.yaml``. Its server URL includes ``/v1``.

The facade accepts these optional operational settings:

.. list-table::
   :header-rows: 1

   * - Variable
     - Default
     - Purpose
   * - ``FATSECRET_WEB_TIMEOUT``
     - ``30``
     - Upstream request timeout in seconds.
   * - ``FATSECRET_WEB_RETRIES``
     - ``true``
     - Enable shared retries for safe upstream GET requests.
   * - ``FATSECRET_WEB_WAIT_ON_RATE_LIMIT``
     - ``true``
     - Wait and replay a mutation only after an explicit ``429`` rejection.
   * - ``FATSECRET_FACADE_DEFAULT_RETRY_AFTER``
     - ``300``
     - Delay used when FatSecret omits ``Retry-After``.
   * - ``FATSECRET_FACADE_MUTATION_DELAY_SECONDS``
     - ``1``
     - Minimum pacing between copied ingredients.
   * - ``FATSECRET_FACADE_HOST``
     - ``127.0.0.1``
     - Server bind address.
   * - ``FATSECRET_FACADE_PORT``
     - ``8000``
     - Server bind port.

Recipe copies
-------------

A copy is a durable asynchronous operation because FatSecret requires one
write per ingredient and can rate-limit the workflow::

   POST /v1/member/recipes/135651874/copies
   Authorization: Bearer <facade token>
   Idempotency-Key: <unique request key>
   Content-Type: application/json

   {"title": "baked beans - 08/26/2026"}

The response is ``202 Accepted`` with an operation URI in ``Location``. Read
that URI until status is ``completed``. A ``waiting`` operation includes
``retry_after`` and can be resumed with::

   POST /v1/member/operations/{operation_id}/resume

Reuse the original idempotency key after a client timeout. A different payload
with the same key returns ``409 Conflict``.

Mutation safety
---------------

The official and member-web clients share retry configuration for safe reads.
Neither client retries mutation requests automatically. Every member-web
mutation is read back and verified. An ambiguous write returns a problem
response with ``upstream_outcome`` set to ``unknown``; reconcile the resource
before issuing another mutation.

The facade serializes writes for its configured account and persists copy
checkpoints and idempotency responses in SQLite. Rendered ingredient text is
not used for copy verification because FatSecret reformats some quantities;
verification compares food IDs, portion IDs, and decimal amounts.
