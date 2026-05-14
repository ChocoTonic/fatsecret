.. _usage:

Migrating from 0.x
==================

In v1.0, every wrapper method has an explicit version suffix matching the
upstream API:

.. code-block:: python

    # Before (0.x):
    foods = fs.foods_search("Tacos")

    # After (1.0):
    foods = fs.foods_search_v5("Tacos")        # latest upstream
    # or, to preserve the 0.x response shape exactly:
    foods = fs.foods_search_v1("Tacos")

The unsuffixed names still exist as deprecation aliases that delegate to
their ``_v1`` replacements and will be removed in v2.0. To surface the
warnings during development::

    python -W default::DeprecationWarning:fatsecret

OAuth2 (client-credentials)
===========================

Public, non-delegated endpoints (food search, food.get, recipes, plus the
Native APIs and Premier-only methods) can be called via OAuth2 by passing
``auth="oauth2"`` and the scopes you need:

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret(
        client_id,
        client_secret,
        auth="oauth2",
        scopes=["basic", "premier", "image-recognition"],
    )

    foods = fs.foods_search_v5("Tacos")

OAuth1 (3-legged) examples
==========================

Fatsecret supports 3-legged OAuth authentication. You can also authenticate to a profile that your application
created.

Web Application
---------------

.. code-block:: python

    from flask import Flask, redirect, url_for, request
    from fatsecret import Fatsecret

    consumer_key = 'Replace with your key'
    consumer_secret = 'Replace with your key'

    app = Flask(__name__)
    fs = Fatsecret(consumer_key, consumer_secret)

    @app.route("/")
    def index():
        if request.args.get('oauth_verifier'):

            verifier_pin = request.args.get('oauth_verifier')

            # Store token as desired. The session is now authenticated
            session_token = fs.authenticate(verifier_pin)

            return redirect(url_for('profile'))

        else:
            return "<a href={0}>Authenticate Access Here</a>".format(url_for('authenticate'))


    @app.route("/auth")
    def authenticate():

        auth_url = fs.get_authorize_url(callback_url="http://127.0.0.1:5000")

        return redirect(auth_url)


    @app.route("/profile")
    def profile():
        food = fs.foods_get_most_eaten()

        return "<h1>Profile</h1><div><strong>Most Eaten Foods</strong><br>{}</div>"\
            .format(food)


    if __name__ == "__main__":
        app.run()

CLI Application
---------------

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret(consumer_key, consumer_secret)

    auth_url = fs.get_authorize_url()

    print("Browse to the following URL in your browser to authorize access:\n{}"\
        .format(auth_url)

    pin = input("Enter the PIN provided by FatSecret: ")
    session_token = fs.authenticate(pin)

    foods = fs.foods_get_most_eaten()
    print("Most Eaten Food Results: {}".format(len(foods)))

Use New Profiles for Your App
-----------------------------

You're able to directly authenticate to any profile that your app has created

.. code-block:: python

    from fatsecret import Fatsecret

    fs = Fatsecret(consumer_key, secret_key)

    session_token = fs.profile_create('new_user_001')

Fatsecret states that each ``session_token`` persists indefinitely for profiles created by your app
so you can store it and use it later as needed.

**Note**: Using a ``session_token`` from a previously authorized session for a Fatsecret user profile
is also possible but Fatsecret isn't as clear about the lifetime of those tokens.

.. code-block:: python

    session_token = # retrieve from your database

Or you can save the ``user_id`` instead and get the ``session_token`` from Fatsecret each time. Keep in mind that
this will only work for profiles created by your application. You'll still need to go through the 3-legged OAuth
process for profiles you didn't create.

.. code-block:: python

    session_token = fs.profile_get_auth('new_user_001')

    new_session = Fatsecret(consumer_key, secret_key, session_token=session_token)