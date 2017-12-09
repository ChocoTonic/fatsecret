Looking for new maintainer
--------------------------

Life and career has taken me in a different direction and I no longer have time to keep this updated. I've attempted to get this merged back into the original with no success. If you're interested in continuing this then let me know.

pyfatsecret
===========

.. image:: https://badge.fury.io/py/fatsecret.svg
    :target: https://badge.fury.io/py/fatsecret

This library provides a lightweight python wrapper for the Fatsecret API with the goal of making it easier to visualize
the data retrieved from the API. To that end, this library will usually return lists of identical elements for ease of
plotting, discarding extra header fields that the Fatsecret API otherwise includes. All API calls return either a
single or list of JSON dictionaries.

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

    foods = fs.foods_search("Tacos")

Refer to the `documentation`_ for further examples and detail

.. _documentation: http://pyfatsecret.readthedocs.org/en/latest/

Contributing
------------

All contributions are welcome! I'm not actively maintaining this library, so there's a good chance that any API changes have not been implemented in this wrapper.
