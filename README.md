# fatsecret

![status](https://badge.fury.io/py/fatsecret.svg)
[![Docs](https://img.shields.io/badge/docs-gh--pages-blue)](https://chocotonic.github.io/fatsecret/)

This library provides a lightweight python wrapper for the Fatsecret API with the goal of making it easier to visualize the data retrieved from the API. To that end, this library will usually return lists of identical elements for ease of plotting, discarding extra header fields that the Fatsecret API otherwise includes. All API calls return either a single or list of JSON dictionaries.

## Installation

```sh
pip install fatsecret
```

Requires Python 3.11+.

## Config

Register for a developer account at [Fatsecret](https://platform.fatsecret.com/api/). You will need your Consumer Key and Consumer Secret key for your application.

## Usage

Fatsecret supports both delegated and public calls. Only through delegated calls can you access Fatsecret user profile data.

If you only need public data:

```py
from fatsecret import Fatsecret

fs = Fatsecret(consumer_key, consumer_secret)
foods = fs.foods_search_v5("Tacos")          # current upstream version
# or, to pin to a specific historical shape:
foods = fs.foods_search_v1("Tacos")
```

Every method carries an explicit `_vN` version suffix matching FatSecret's
multi-version API. Unsuffixed names (`foods_search`, `food_get`, …) still
exist as `DeprecationWarning`-emitting aliases and will be removed in
v2.0. Surface the warnings during development:

```sh
python -W default::DeprecationWarning:fatsecret your_script.py
```

For OAuth2 client-credentials (required for Premier / Native endpoints):

```py
fs = Fatsecret(client_id, client_secret, auth="oauth2", scopes=["basic", "premier"])
```

Refer to the [documentation](https://chocotonic.github.io/fatsecret/) for further examples and detail.

## Documentation

Docs are published to GitHub Pages at [chocotonic.github.io/fatsecret](https://chocotonic.github.io/fatsecret/). Every released tag gets its own permanent URL at `https://chocotonic.github.io/fatsecret/vX.Y.Z/` (e.g. [`v1.5.6`](https://chocotonic.github.io/fatsecret/v1.5.6/), [`v1.4.1`](https://chocotonic.github.io/fatsecret/v1.4.1/), [`v0.5.0`](https://chocotonic.github.io/fatsecret/v0.5.0/)), so version-pinned URLs never 404. See [the all-versions index](https://chocotonic.github.io/fatsecret/) for the full list.

## Contributing

All contributions are welcome! I'm not actively maintaining this library, so there's a good chance that any API changes have not been implemented in this wrapper.
