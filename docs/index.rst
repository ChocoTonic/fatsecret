FatSecret
=========

This library provides a lightweight python wrapper for the Fatsecret API with the goal of making it easier to visualize
the data retrieved from the API. To that end, this library will usually return lists of identical elements for ease of
plotting, discarding extra header fields that the Fatsecret API otherwise includes. All API calls return either a
single or list of JSON dictionaries.

.. note::

   **v1.0 is a breaking release.** Every method now has an explicit version
   suffix (e.g. ``foods_search_v5``). The unsuffixed names from 0.x remain
   as deprecation aliases until v2.0. Run with
   ``python -W default::DeprecationWarning:fatsecret`` to surface them.

Installation
------------
Install the module via pip::

    $ pip install fatsecret

or easy_install::

    $ easy_install fatsecret

Config
------
Register for a developer account at `Fatsecret`_. You will need your Consumer Key and Consumer Secret key for
your application.

.. _Fatsecret: http://platform.fatsecret.com/api/

Usage
-----

Fatsecret supports both delegated and public calls. Only through delegated calls can you access Fatsecret user
profile data.

If you're only interested in the public data you only require a session to make HTTP requests:

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret(consumer_key, consumer_secret)

Once you have created a session then you can start reading from Fatsecret's public food and recipe database

.. code-block:: python

    foods = fs.foods_search_v5("Tacos")        # latest upstream version

OAuth Examples
--------------

You will need to authenticate to a Fatsecret user profile via OAuth 1.0 in order to access profile specific
data such as the meal diary, favorite meals, etc.

.. toctree::
    :maxdepth: 2

    usage

API Reference
-------------
.. toctree::
    :maxdepth: 2

    api
