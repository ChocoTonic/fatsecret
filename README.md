# fatsecret

![status](https://badge.fury.io/py/fatsecret.svg)
[![Documentation Status](https://readthedocs.org/projects/fatsecret/badge/?version=latest)](https://fatsecret.readthedocs.io/en/latest/?badge=latest)

This library provides a lightweight python wrapper for the Fatsecret API with the goal of making it easier to visualize the data retrieved from the API. To that end, this library will usually return lists of identical elements for ease of plotting, discarding extra header fields that the Fatsecret API otherwise includes. All API calls return either a single or list of JSON dictionaries.

## Installation

Install the module via pip

```sh
$ pip install fatsecret
```

or easy_install::

```sh
$ easy_install fatsecret
```

## Config

Register for a developer account at [Fatsecret](https://platform.fatsecret.com/api/). You will need your Consumer Key and Consumer Secret key for your application.

## Usage

Fatsecret supports both delegated and public calls. Only through delegated calls can you access Fatsecret user profile data.

If you're only interested in the public data you only require a session to make HTTP requests:

```py
from fatsecret import Fatsecret

fs = Fatsecret(consumer_key, consumer_secret)
```

Once you have created a session then you can start reading from Fatsecret's public food and recipe database

```py
foods = fs.foods_search("Tacos")
```

Refer to the [documentation](https://fatsecret.readthedocs.io/en/latest/) for further examples and detail.

## Documentation

- **Current docs** — [fatsecret.readthedocs.io](https://fatsecret.readthedocs.io/), built automatically by Read the Docs (`latest` tracks `master`, `stable` tracks the highest released tag).
- **Per-version docs** — `https://chocotonic.github.io/fatsecret/vX.Y.Z/` for any released tag (e.g. [`v1.4.1`](https://chocotonic.github.io/fatsecret/v1.4.1/), [`v1.2.1`](https://chocotonic.github.io/fatsecret/v1.2.1/), [`v0.5.0`](https://chocotonic.github.io/fatsecret/v0.5.0/)). A static per-tag snapshot is published to `gh-pages` so version-pinned URLs never 404. See [the all-versions index](https://chocotonic.github.io/fatsecret/) for a full list.

## Contributing

All contributions are welcome! I'm not actively maintaining this library, so there's a good chance that any API changes have not been implemented in this wrapper.
