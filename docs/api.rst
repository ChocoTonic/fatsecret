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
and are grouped under top-level guide categories matching FatSecret's
official documentation layout (`platform.fatsecret.com/docs/guides/
<https://platform.fatsecret.com/docs/guides/>`_). Each guide contains one
subsection per OpenAPI tag (sourced from
``docs/api-spec/openapi.generated.yaml``). Client-only helpers (auth
handshake, session lifecycle, time conversion) are listed at the bottom
under **Client utilities**.

.. fatsecret-api-groups::
