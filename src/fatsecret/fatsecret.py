"""
fatsecret
---------

Simple python wrapper of the Fatsecret API

"""

import datetime
import time
from typing import Any, List, Literal, Optional, Tuple, Union

from urllib.parse import parse_qs

import requests
import tenacity
from bs4 import BeautifulSoup
from oauthlib.oauth1 import SIGNATURE_TYPE_QUERY
from requests_oauthlib import OAuth1Session

from ._retry import default_policy
from .errors import (
    ApplicationError,
    AuthenticationError,
    GeneralError,
    ParameterError,
    PremierRequiredError,
    ScopeRequiredError,
)


class Fatsecret:

    # ========================= CORE =========================

    """Core FatSecret API client logic (auth, request handling, utilities)."""

    REQUEST_TOKEN_URL = "https://authentication.fatsecret.com/oauth/request_token"
    AUTHORIZE_URL = "https://authentication.fatsecret.com/oauth/authorize"
    ACCESS_TOKEN_URL = "https://authentication.fatsecret.com/oauth/access_token"
    BASE_URL = "https://platform.fatsecret.com/rest/server.api"
    OAUTH2_TOKEN_URL = "https://oauth.fatsecret.com/connect/token"

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        session_token: Optional[Tuple[str, str]] = None,
        auth: Literal["oauth1", "oauth2"] = "oauth1",
        scopes: Optional[List[str]] = None,
        retries: Union[bool, tenacity.Retrying] = True,
    ):
        """Initialize the FatSecret API session.

        Args:
            consumer_key: API consumer/client key (register at https://platform.fatsecret.com/api)
            consumer_secret: API consumer/client secret
            session_token: Optional (token, secret) tuple for an existing OAuth1 session
            auth: "oauth1" (default, three-legged, supports user-scoped methods)
                  or "oauth2" (client-credentials, required for native/Premier methods)
            scopes: OAuth2 scopes to request. Only used when auth="oauth2".
                    Valid scopes: basic, premier, barcode, localization, nlp,
                    image-recognition, feedback. None requests all scopes the
                    client has access to.
            retries: Retry policy for transient GET failures. ``True`` (default)
                installs the SDK's exponential-backoff + full-jitter policy
                (3 attempts, 30s total cap, honors numeric ``Retry-After``).
                ``False`` disables retries entirely. Pass a configured
                ``tenacity.Retrying`` instance for full custom control.
                Mutating requests (POST/PUT/DELETE) are never retried.
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth_mode: Literal["oauth1", "oauth2"] = auth
        self.scopes = scopes
        self._retries: Optional[tenacity.Retrying] = (
            None
            if retries is False
            else retries
            if isinstance(retries, tenacity.Retrying)
            else default_policy()
        )

        self.request_token = None
        self.request_token_secret = None
        self.access_token = None
        self.access_token_secret = None

        self._oauth2_token: Optional[str] = None
        self._oauth2_token_expires_at: float = 0.0

        if auth == "oauth1":
            if session_token:
                self.access_token = session_token[0]
                self.access_token_secret = session_token[1]
                self.session = OAuth1Session(
                    consumer_key,
                    client_secret=consumer_secret,
                    resource_owner_key=session_token[0],
                    resource_owner_secret=session_token[1],
                    signature_type=SIGNATURE_TYPE_QUERY,
                )
            else:
                self.session = OAuth1Session(
                    consumer_key,
                    client_secret=consumer_secret,
                    callback_uri="oob",
                    signature_type=SIGNATURE_TYPE_QUERY,
                )
        elif auth == "oauth2":
            self.session = requests.Session()
        else:
            raise ValueError(f"auth must be 'oauth1' or 'oauth2', got {auth!r}")

        # v2.0 resource-namespaced surface. Each resource exposes the
        # OAS-tag's endpoints via short names (e.g. fs.foods.search_v5).
        from .resources import (
            ClassificationResource,
            DiaryResource,
            ExercisesResource,
            FeedbackResource,
            FoodsResource,
            MealsResource,
            NativeResource,
            ProfileFoodsResource,
            ProfileResource,
            RecipesResource,
            WeightResource,
        )

        self.foods = FoodsResource(self)
        self.classification = ClassificationResource(self)
        self.recipes = RecipesResource(self)
        self.profile_foods = ProfileFoodsResource(self)
        self.meals = MealsResource(self)
        self.diary = DiaryResource(self)
        self.exercises = ExercisesResource(self)
        self.weight = WeightResource(self)
        self.profile = ProfileResource(self)
        self.native = NativeResource(self)
        self.feedback = FeedbackResource(self)

    def _get_oauth2_token(self) -> str:
        """Fetch (and cache) an OAuth2 bearer token via client_credentials.

        Tokens are cached in-memory and refreshed shortly before expiry.
        """
        now = time.time()
        if self._oauth2_token and now < self._oauth2_token_expires_at - 30:
            return self._oauth2_token

        data: dict = {"grant_type": "client_credentials"}
        if self.scopes:
            data["scope"] = " ".join(self.scopes)
        resp = requests.post(
            self.OAUTH2_TOKEN_URL,
            data=data,
            auth=(self.consumer_key, self.consumer_secret),
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        self._oauth2_token = payload["access_token"]
        self._oauth2_token_expires_at = now + int(payload.get("expires_in", 86400))
        return self._oauth2_token

    def _call(
        self,
        params: dict,
        *,
        url: Optional[str] = None,
        method: str = "GET",
        json_body: Optional[dict] = None,
    ) -> Any:
        """Unified request entrypoint used by all _vN methods.

        Routes through OAuth1 or OAuth2 based on `auth_mode`. Always parses
        the JSON response, runs `_check_errors`, and returns the decoded body.
        Response unwrapping is the caller's responsibility via `_unwrap`.
        """
        params = dict(params)
        params.setdefault("format", "json")
        target = url or self.api_url

        if self.auth_mode == "oauth2":
            headers = {"Authorization": f"Bearer {self._get_oauth2_token()}"}
        else:
            headers = None

        def _do() -> requests.Response:
            r = self.session.request(
                method,
                target,
                params=params,
                json=json_body,
                headers=headers,
                timeout=30,
            )
            # Surface transport-level HTTP failures (5xx, 429, etc.) as
            # `HTTPError` so the retry policy can classify them. FatSecret's
            # own error envelopes are served with HTTP 200 and handled below
            # by `_check_errors`, so this does not regress that path. A
            # non-transient 4xx (e.g. 401) propagates straight out — the
            # retry classifier only matches the transient set.
            r.raise_for_status()
            return r

        if self._retries is not None and method == "GET":
            resp = self._retries(_do)
        else:
            resp = _do()

        payload = resp.json()
        self._check_errors(payload)
        return payload

    @staticmethod
    def _check_errors(payload: Any) -> None:
        """Raise a typed exception if `payload` is an error envelope. No-op otherwise.

        Maps upstream error codes to the closest typed exception subclass.
        See https://platform.fatsecret.com/docs/guides/error-codes for the
        canonical list.
        """
        if not isinstance(payload, dict):
            return
        err = payload.get("error")
        if not err:
            return
        code = err.get("code")
        message = err.get("message", "")

        if code == 2:
            raise AuthenticationError(2, "This api call requires an authenticated session")
        if code in (3, 4, 5, 6, 7, 8, 9):
            raise AuthenticationError(code, message)
        if code in (1, 10, 11, 12, 13, 14, 20, 21, 22, 23, 24):
            raise GeneralError(code, message)
        if 101 <= code <= 109:
            raise ParameterError(code, message)
        if code == 207:
            # Premier scope required
            raise PremierRequiredError(code, message)
        if code in (208, 211):
            # Other scope-related rejections (image-recognition, nlp, barcode, etc.)
            raise ScopeRequiredError(code, message)
        if 201 <= code <= 211:
            raise ApplicationError(code, message)
        raise ApplicationError(code, message)

    @staticmethod
    def _unwrap(payload: Any, *path: str, list_key: Optional[str] = None) -> Any:
        """Walk `path` keys into `payload`. If `list_key` is set, coerce the
        terminal value into a list (FatSecret returns a single dict when there's
        one item, an array when there are many; `_unwrap` normalizes that to
        `list[dict]` always).

        Examples:
            _unwrap({"foods": {"food": [...]}}, "foods", list_key="food") -> list
            _unwrap({"foods_search": {"results": {"food": {...}}}},
                    "foods_search", "results", list_key="food") -> [{...}]
            _unwrap({"month": {"day": [...]}}, "month", list_key="day") -> list
        """
        cur: Any = payload
        for key in path:
            if cur is None:
                return [] if list_key else None
            if not isinstance(cur, dict):
                return [] if list_key else None
            cur = cur.get(key)
        if list_key is None:
            return cur
        if cur is None:
            return []
        if isinstance(cur, dict) and list_key in cur:
            inner = cur[list_key]
        else:
            inner = cur
        if inner is None:
            return []
        return inner if isinstance(inner, list) else [inner]

    @property
    def api_url(self) -> str:
        return self.BASE_URL

    def get_authorize_url(self, callback_url: str = "oob") -> str:
        """Fetch an OAuth1 request token and return the user-facing authorize URL.

        Args:
            callback_url: Absolute URL to redirect the user to after they authorize,
                or ``"oob"`` (out-of-band) to receive a verifier PIN.
        Returns:
            The authorize URL with the freshly minted ``oauth_token`` appended.
        """
        # If the caller asked for a non-default callback, rebuild the session
        # so the right callback_uri is folded into the request-token signature.
        if callback_url != "oob":
            self.session = OAuth1Session(
                self.consumer_key,
                client_secret=self.consumer_secret,
                callback_uri=callback_url,
                signature_type=SIGNATURE_TYPE_QUERY,
            )

        # FatSecret's request-token endpoint only accepts GET. requests-oauthlib's
        # fetch_request_token() forces POST, so issue the signed GET ourselves.
        resp = self.session.get(self.REQUEST_TOKEN_URL)
        resp.raise_for_status()
        token = {k: v[0] for k, v in parse_qs(resp.text).items()}
        if "oauth_token" not in token:
            raise RuntimeError(
                f"Token request failed: {resp.status_code} {resp.text!r}"
            )
        self.request_token = token["oauth_token"]
        self.request_token_secret = token["oauth_token_secret"]
        # Promote request token onto the session so authorization_url can find it.
        self.session._client.client.resource_owner_key = self.request_token
        self.session._client.client.resource_owner_secret = self.request_token_secret
        return self.session.authorization_url(self.AUTHORIZE_URL)

    def authenticate(self, verifier: Union[str, int]) -> Tuple[str, str]:
        """Exchange the verifier (PIN or callback code) for permanent access tokens.

        Args:
            verifier: PIN displayed to user or returned via callback.
        Returns:
            (access_token, access_secret)
        """
        # Re-instantiate session with request token + verifier so the GET
        # below is signed correctly. FatSecret's access-token endpoint also
        # only accepts GET, so we issue it directly rather than going through
        # fetch_access_token() (which would force POST).
        self.session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.request_token,
            resource_owner_secret=self.request_token_secret,
            verifier=str(verifier),
            signature_type=SIGNATURE_TYPE_QUERY,
        )
        resp = self.session.get(self.ACCESS_TOKEN_URL)
        resp.raise_for_status()
        token = {k: v[0] for k, v in parse_qs(resp.text).items()}
        if "oauth_token" not in token:
            raise RuntimeError(
                f"Access-token exchange failed: {resp.status_code} {resp.text!r}"
            )
        self.access_token = token["oauth_token"]
        self.access_token_secret = token["oauth_token_secret"]

        # Replace with a long-lived authed session for subsequent API calls.
        self.session = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret,
            signature_type=SIGNATURE_TYPE_QUERY,
        )

        return (self.access_token, self.access_token_secret)

    def close(self) -> None:
        """Close the current HTTP session."""
        self.session.close()

    @staticmethod
    def unix_time(dt: datetime.datetime) -> int:
        """Convert a datetime to number of days since the Epoch (FatSecret style)."""
        epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc).replace(
            tzinfo=None
        )
        delta = dt - epoch
        return delta.days

    @staticmethod
    def unix_time_v2(dt: Union[datetime.datetime, datetime.date, int, float]) -> int:
        """Convert datetime/date/timestamp into number of days since 1970-01-01."""
        epoch = datetime.datetime(1970, 1, 1)
        if isinstance(dt, datetime.datetime):
            delta = dt - epoch
            return delta.days
        elif isinstance(dt, datetime.date):
            delta = datetime.datetime(dt.year, dt.month, dt.day) - epoch
            return delta.days
        elif isinstance(dt, (int, float)):
            # treat as unix timestamp, use timezone-aware UTC
            dt_utc = datetime.datetime.fromtimestamp(
                dt, tz=datetime.timezone.utc
            ).replace(tzinfo=None)
            delta = dt_utc - epoch
            return delta.days
        else:
            raise TypeError("dt must be datetime, date, int, or float")

    @staticmethod
    def valid_response(response: requests.Response):
        """Validate a JSON API response and extract its data or raise an error."""
        if response.json():

            for key in response.json():

                # Error Code Handling
                if key == "error":
                    code = response.json()[key]["code"]
                    message = response.json()[key]["message"]
                    if code == 2:
                        raise AuthenticationError(
                            2, "This api call requires an authenticated session"
                        )

                    elif code in [1, 10, 11, 12, 20, 21]:
                        raise GeneralError(code, message)

                    elif 3 <= code <= 9:
                        raise AuthenticationError(code, message)

                    elif 101 <= code <= 108:
                        raise ParameterError(code, message)

                    elif 201 <= code <= 207:
                        raise ApplicationError(code, message)

                # All other response options
                elif key == "success":
                    return True

                elif key == "foods":
                    return response.json()[key]["food"]

                elif key == "suggestions":
                    return response.json()[key]

                elif key == "recipes":
                    return response.json()[key]["recipe"]

                elif key == "saved_meals":
                    return response.json()[key]["saved_meal"]

                elif key == "saved_meal_items":
                    return response.json()[key]["saved_meal_item"]

                elif key == "exercise_types":
                    return response.json()[key]["exercise"]

                elif key == "food_entries":
                    if response.json()[key] is None:
                        return []
                    entries = response.json()[key]["food_entry"]
                    if isinstance(entries, dict):
                        return [entries]
                    elif isinstance(entries, list):
                        return entries

                elif key == "month":
                    return response.json()[key]["day"]

                elif key == "profile":
                    if "auth_token" in response.json()[key]:
                        return (
                            response.json()[key]["auth_token"],
                            response.json()[key]["auth_secret"],
                        )
                    else:
                        return response.json()[key]

                elif key in (
                    "food",
                    "recipe",
                    "recipe_types",
                    "saved_meal_id",
                    "saved_meal_item_id",
                    "food_entry_id",
                ):
                    return response.json()[key]

    # ========================= AUTH =========================

    def fatsecret_authenticate(
        username: str, password: str, consumer_key: str, consumer_secret: str
    ):
        """Authenticate a user programmatically using credentials and return an authorized Fatsecret instance.

        Note:
        This uses HTML form emulation against FatSecret's login flow and may break if the website changes.
        It is provided for convenience and developer testing, not production OAuth flows.
        """
        try:
            session = requests.Session()
            fatsecret_client = Fatsecret(consumer_key, consumer_secret)
            authorize_url = fatsecret_client.get_authorize_url().replace(
                "authorize", "authorize.aspx"
            )

            # Fetch viewstate and generator dynamically
            login_page_response = session.get(url=authorize_url)
            login_page_soup = BeautifulSoup(login_page_response.text, "lxml")
            viewstate_value = login_page_soup.find("input", {"name": "__VIEWSTATE"})[
                "value"
            ]
            viewstate_generator_value = login_page_soup.find(
                "input", {"name": "__VIEWSTATEGENERATOR"}
            )["value"]

            payload = {
                "__VIEWSTATE": viewstate_value,
                "__VIEWSTATEGENERATOR": viewstate_generator_value,
                "Name": username,
                "Password": password,
                "Login.x": 0,
                "Login.y": 0,
            }

            pin_response = session.post(url=authorize_url, data=payload)
            pin_soup = BeautifulSoup(pin_response.content, "lxml")
            verifier_tag = pin_soup.find("b")
            if not verifier_tag:
                raise RuntimeError(
                    "Failed to find PIN in response. Login may have failed."
                )
            verifier_pin = verifier_tag.text.strip()
            print(f"Obtained verifier PIN. {len(verifier_pin) = }")
            fatsecret_client.authenticate(verifier_pin)
            print("Authentication successful.")
            return fatsecret_client
        except Exception as error:
            message = f"Failed to authenticate:\n{error}"
            print(message)
            return None

    # ========================= HELPERS =========================
    # Shared helpers used by the namespaced resource implementations.

    @staticmethod
    def _set_optional(params: dict, items: list) -> None:
        """Helper: add (key, value) pairs to params only when value is not None."""
        for k, v in items:
            if v is not None:
                params[k] = v

    @staticmethod
    def _mutator_success(payload: Any) -> Union[bool, Any]:
        """Helper: collapse a `{"success": 1}` payload into True; pass-through otherwise."""
        if isinstance(payload, dict) and "success" in payload:
            return payload["success"] == 1 or payload["success"] == "1"
        return payload
