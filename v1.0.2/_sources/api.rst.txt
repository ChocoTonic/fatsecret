API Documentation
=================

As of v1.0 every endpoint method carries an explicit ``_vN`` suffix matching
the upstream API version (e.g. ``foods_search_v5``, ``food_get_v5``,
``recipes_search_v3``). The unsuffixed legacy names (``foods_search``,
``food_get``, ...) remain available as **deprecated aliases** for the v1.x
line and emit :class:`DeprecationWarning` when called. To surface those
warnings during development, run Python with::

    python -W default::DeprecationWarning:fatsecret

.. autoclass:: fatsecret.Fatsecret
    :members:
    :noindex:
    :exclude-members: __init__
