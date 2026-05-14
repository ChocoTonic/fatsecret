"""
fatsecret
---------

Simple python wrapper of the Fatsecret API

"""

import base64
import datetime
import hashlib
import hmac
import time
import urllib
import uuid
import warnings
from typing import Any, List, Literal, Optional, Tuple, Union

import requests
from bs4 import BeautifulSoup
from rauth.service import OAuth1Service

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
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth_mode: Literal["oauth1", "oauth2"] = auth
        self.scopes = scopes

        self.request_token = None
        self.request_token_secret = None
        self.access_token = None
        self.access_token_secret = None

        self._oauth2_token: Optional[str] = None
        self._oauth2_token_expires_at: float = 0.0

        if auth == "oauth1":
            self.oauth = OAuth1Service(
                name="fatsecret",
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                request_token_url=self.REQUEST_TOKEN_URL,
                authorize_url=self.AUTHORIZE_URL,
                access_token_url=self.ACCESS_TOKEN_URL,
                base_url=self.BASE_URL,
            )
            if session_token:
                self.access_token = session_token[0]
                self.access_token_secret = session_token[1]
                self.session = self.oauth.get_session(token=session_token)
            else:
                self.session = self.oauth.get_session()
        elif auth == "oauth2":
            self.oauth = None
            self.session = requests.Session()
        else:
            raise ValueError(f"auth must be 'oauth1' or 'oauth2', got {auth!r}")

        # v2.0 resource-namespaced surface. Each resource exposes the
        # OAS-tag's endpoints via short names (e.g. fs.foods.search_v5).
        # Phase 1: pure delegation over the flat _vN methods on this class.
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
            resp = self.session.request(
                method, target, params=params, json=json_body, headers=headers, timeout=30
            )
        else:
            resp = self.session.request(
                method, target, params=params, json=json_body, timeout=30
            )

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
        if self.auth_mode == "oauth1" and self.oauth is not None:
            return self.oauth.base_url
        return self.BASE_URL

    def get_authorize_url(self, callback_url: str = "oob") -> str:
        """
        New implementation using manual OAuth 1.0 flow to /oauth/request_token on the new endpoint.

        :param callback_url: An absolute URL to redirect the User to when they have completed authentication
        :type callback_url: str
        """
        print("Generating request token...")

        oauth_consumer_key = self.consumer_key
        oauth_consumer_secret = self.consumer_secret
        oauth_signature_method = "HMAC-SHA1"
        oauth_timestamp = str(int(time.time()))
        oauth_nonce = str(uuid.uuid4().hex)
        oauth_version = "1.0"
        oauth_callback = callback_url

        # Collect parameters for base string
        params = {
            "oauth_consumer_key": oauth_consumer_key,
            "oauth_signature_method": oauth_signature_method,
            "oauth_timestamp": oauth_timestamp,
            "oauth_nonce": oauth_nonce,
            "oauth_version": oauth_version,
            "oauth_callback": oauth_callback,
        }

        base_params = "&".join(
            [
                "{}={}".format(
                    urllib.parse.quote(k, safe=""), urllib.parse.quote(v, safe="")
                )
                for k, v in sorted(params.items())
            ]
        )
        method = "POST"
        base_url = self.oauth.request_token_url
        signature_base_string = "&".join(
            [
                method,
                urllib.parse.quote(base_url, safe=""),
                urllib.parse.quote(base_params, safe=""),
            ]
        )

        signing_key = f"{urllib.parse.quote(oauth_consumer_secret, safe='')}&"

        hashed = hmac.new(
            signing_key.encode("utf-8"),
            signature_base_string.encode("utf-8"),
            hashlib.sha1,
        )
        oauth_signature = base64.b64encode(hashed.digest()).decode()

        params["oauth_signature"] = oauth_signature

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        full_request_url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print("Full request URL ends with:", full_request_url[-4:])

        # POST request to fetch request_token
        response = requests.post(base_url, data=params, headers=headers)
        response.raise_for_status()
        result = dict(urllib.parse.parse_qsl(response.text))

        self.request_token = result["oauth_token"]
        self.request_token_secret = result["oauth_token_secret"]
        print(f"Request token ends with: {self.request_token[-4:]}")
        print(f"secret ends with: {self.request_token_secret[-4:]}")

        return f"{self.oauth.authorize_url}?oauth_token={self.request_token}"

    def authenticate(self, verifier: Union[str, int]) -> Tuple[str, str]:
        """Exchange the verifier (PIN or callback code) for permanent access tokens.

        Args:
            verifier: PIN displayed to user or returned via callback.
        Returns:
            (access_token, access_secret)
        """
        session_token = self.oauth.get_access_token(
            self.request_token,
            self.request_token_secret,
            params={"oauth_verifier": verifier},
        )

        self.access_token = session_token[0]
        self.access_token_secret = session_token[1]
        self.session = self.oauth.get_session(session_token)

        # Return session token for app specific caching
        return session_token

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

    # ========================= EXERCISES =========================

    def exercises_get(self):
        """This is a utility method, returning the full list of all supported exercise type names and
        their associated unique identifiers.

        .. deprecated:: 1.0
            Use :meth:`exercises_get_v1` for identical behavior or
            :meth:`exercises_get_v2` for the current upstream version.
            This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.exercises_get() is deprecated and will be removed in v2.0; "
            "use exercises_get_v1() to preserve current behavior or exercises_get_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercises_get_v1()

    def exercise_entries_commit_day(self, date=None):
        """Saves the default exercise entries for the user on a nominated date.

        .. deprecated:: 1.0
            Use :meth:`exercise_entries_commit_day_v1`. This alias will be removed in v2.0.

        :param date: Date to save default exercises on (default value is the current day).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.exercise_entries_commit_day() is deprecated and will be removed in v2.0; "
            "use exercise_entries_commit_day_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercise_entries_commit_day_v1(date=date)

    def exercise_entries_get(self, date=None):
        """Returns the daily exercise entries for the user on a nominated date.
        The API will always return 24 hours worth of exercise entries for a given user on a given date.
        These entries will either be "template" entries (which a user may override for any given day of the week)
        or saved exercise entry values.

        .. deprecated:: 1.0
            Use :meth:`exercise_entries_get_v1` for identical behavior or
            :meth:`exercise_entries_get_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param date: Day of exercises to retrieve (default value is the current day).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.exercise_entries_get() is deprecated and will be removed in v2.0; "
            "use exercise_entries_get_v1() to preserve current behavior or exercise_entries_get_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercise_entries_get_v1(date=date)

    def exercise_entries_get_month(self, date=None):
        """Returns the summary estimated daily calories expended for a user's exercise diary entries for
        the month specified. Use this call to display total energy expenditure information to users about their
        exercise and activities for a nominated month.

        .. deprecated:: 1.0
            Use :meth:`exercise_entries_get_month_v1` for identical behavior or
            :meth:`exercise_entries_get_month_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param date: Day within month to retrieve (default value is the current day for the current month).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.exercise_entries_get_month() is deprecated and will be removed in v2.0; "
            "use exercise_entries_get_month_v1() to preserve current behavior or "
            "exercise_entries_get_month_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercise_entries_get_month_v1(date=date)

    def exercise_entries_save_template(self, days, date=None):
        """
        Takes the set of exercise entries on a nominated date and saves these entries as "template"
        entries for nominated days of the week.

        .. deprecated:: 1.0
            Use :meth:`exercise_entries_save_template_v1`. Note that v1 fixes the legacy
            bug that erroneously hit ``exercise_entries.get_month``; the alias now delegates
            to the corrected method. This alias will be removed in v2.0.

        :param days: The days of the week specified as bits with Sunday being the 1st bit and Saturday being the last.
            For example, Tuesday and Thursday would be represented as 00010100 in bits where Tuesday is the 3rd
            bit from the right and Thursday being the 5th.

        :type days: str
        :param date: Day of exercises to use as the template (default value is the current day).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.exercise_entries_save_template() is deprecated and will be removed in v2.0; "
            "use exercise_entries_save_template_v1() (which also fixes the legacy bug that hit "
            "exercise_entries.get_month).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercise_entries_save_template_v1(int(days), date=date)

    def exercise_entry_edit(
        self,
        shift_to_id,
        shift_from_id,
        minutes,
        date=None,
        shift_to_name=None,
        shift_from_name=None,
        kcals=None,
    ):
        """
        Records a change to a user's exercise diary entry for a nominated date.
        All changes to an exercise diary involve either increasing the duration of an existing activity or
        introducing a new activity for a nominated duration. Because there are always 24 hours worth of exercise
        entries on any given date, the user must nominate the exercise or activity from which the time was taken
        to balance out the total duration of activities and exercises for the 24 hour period. As such, each change
        to the exercise entries on a given day is a "shifting" operation where time is moved from one activity to
        another. An exercise is removed from the day when all of the time allocated to it is shifted to other exercises.

        :param shift_to_id: The ID of the exercise type to shift to.
        :type shift_to_id: str
        :param shift_from_id: The ID of the exercise type to shift from.
        :type shift_from_id: str
        :param minutes: The number of minutes to shift.
        :type minutes: int
        :param date: Day to edit (default value is the current day).
        :type date: datetime.datetime
        :param shift_to_name: Only required if shift_to_id is 0 (exercise type "Other").
            This is the name of the new custom exercise type to shift to.

        :type shift_to_name: str
        :param shift_from_name: Only required if shift_from_id is 0 (exercise type "Other").
            This is the name of the custom exercise type to shift from.

        :type shift_from_name: str
        :param kcals: Number of calories burned
        :type kcals: int

        .. deprecated:: 1.0
            Use :meth:`exercise_entry_edit_v1`. This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.exercise_entry_edit() is deprecated and will be removed in v2.0; "
            "use exercise_entry_edit_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.exercise_entry_edit_v1(
            shift_to_id,
            shift_from_id,
            minutes,
            date=date,
            shift_to_name=shift_to_name,
            shift_from_name=shift_from_name,
            kcal=kcals,
        )

    # ========================= FOODS =========================

    def food_add_favorite(self, food_id, serving_id=None, number_of_units=None):
        """Add a food to a user's favorite according to the parameters specified.

        .. deprecated:: 1.0
            Use :meth:`food_add_favorite_v1`. This alias will be removed in v2.0.

        :param food_id: The ID of the favorite food to add.
        :type food_id: str
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :type serving_id: str
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        :type number_of_units: float
        """
        warnings.warn(
            "Fatsecret.food_add_favorite() is deprecated and will be removed in v2.0; "
            "use food_add_favorite_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_add_favorite_v1(
            food_id, serving_id=serving_id, number_of_units=number_of_units
        )

    def food_delete_favorite(self, food_id, serving_id=None, number_of_units=None):
        """Delete the food to a user's favorite according to the parameters specified.

        .. deprecated:: 1.0
            Use :meth:`food_delete_favorite_v1`. This alias will be removed in v2.0.

        :param food_id: The ID of the favorite food to add.
        :type food_id: str
        :param serving_id: Only required if number_of_units is present. This is the ID of the favorite serving.
        :type serving_id: str
        :param number_of_units: Only required if serving_id is present. This is the favorite number of servings.
        :type number_of_units: float
        """
        warnings.warn(
            "Fatsecret.food_delete_favorite() is deprecated and will be removed in v2.0; "
            "use food_delete_favorite_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_delete_favorite_v1(
            food_id, serving_id=serving_id, number_of_units=number_of_units
        )

    def food_get(self, food_id):
        """Returns detailed nutritional information for the specified food.
        Use this call to display nutrition values for a food to users.

        .. deprecated:: 1.0
            Use :meth:`food_get_v1` for identical behavior or :meth:`food_get_v5` for
            the current upstream version. This alias will be removed in v2.0.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """
        warnings.warn(
            "Fatsecret.food_get() is deprecated and will be removed in v2.0; "
            "use food_get_v1() to preserve current behavior or food_get_v5() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_get_v1(food_id)

    def food_get_v2(self, food_id, region=None, language=None):
        """Returns detailed nutritional information for the specified food.
        Use this call to display nutrition values for a food to users.

        :param food_id: Fatsecret food identifier
        :type food_id: str
        """
        params = {"method": "food.get.v2", "food_id": food_id, "format": "json"}
        if region:
            params["region"] = region
        if language:
            params["language"] = language
        response = self.session.get(self.api_url, params=params)
        return self.valid_response(response)

    def food_find_id_for_barcode(self, barcode, region=None, language=None):
        """
        Returns the food_id matching the barcode specified.

        Barcodes must be specified as GTIN-13 numbers - a 13-digit number filled in with
        zeros for the spaces to the left. UPC-A, EAN-13 and EAN-8 barcodes may be specified.
        UPC-E barcodes should be converted to their UPC-A equivalent (and then specified
        as GTIN-13 numbers).

        .. deprecated:: 1.0
            Use :meth:`food_find_id_for_barcode_v1` for identical behavior or
            :meth:`food_find_id_for_barcode_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param barcode: The 13-digit GTIN-13 formatted sequence of digits representing
            the barcode to search against.
        :type barcode: str

        :param region: Optional region code.
        :type region: str

        :param language: Optional language code.
        :type language: str
        """
        warnings.warn(
            "Fatsecret.food_find_id_for_barcode() is deprecated and will be removed in v2.0; "
            "use food_find_id_for_barcode_v1() to preserve current behavior or "
            "food_find_id_for_barcode_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_find_id_for_barcode_v1(
            barcode, region=region, language=language
        )

    def foods_get_favorites(self):
        """Returns the favorite foods for the authenticated user.

        .. deprecated:: 1.0
            Use :meth:`foods_get_favorites_v1` for identical behavior or
            :meth:`foods_get_favorites_v2` for the current upstream version.
            This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.foods_get_favorites() is deprecated and will be removed in v2.0; "
            "use foods_get_favorites_v1() to preserve current behavior or "
            "foods_get_favorites_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.foods_get_favorites_v1()

    def foods_get_most_eaten(self, meal=None):
        """Returns the most eaten foods for the user according to the meal specified.

        .. deprecated:: 1.0
            Use :meth:`foods_get_most_eaten_v1` for identical behavior or
            :meth:`foods_get_most_eaten_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        warnings.warn(
            "Fatsecret.foods_get_most_eaten() is deprecated and will be removed in v2.0; "
            "use foods_get_most_eaten_v1() to preserve current behavior or "
            "foods_get_most_eaten_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        meal_arg = meal if meal in ["breakfast", "lunch", "dinner", "other"] else None
        return self.foods_get_most_eaten_v1(meal=meal_arg)

    def foods_get_recently_eaten(self, meal=None):
        """Returns the recently eaten foods for the user according to the meal specified

        .. deprecated:: 1.0
            Use :meth:`foods_get_recently_eaten_v1` for identical behavior or
            :meth:`foods_get_recently_eaten_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param meal: 'breakfast', 'lunch', 'dinner', or 'other'
        :type meal: str
        """
        warnings.warn(
            "Fatsecret.foods_get_recently_eaten() is deprecated and will be removed in v2.0; "
            "use foods_get_recently_eaten_v1() to preserve current behavior or "
            "foods_get_recently_eaten_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        meal_arg = meal if meal in ["breakfast", "lunch", "dinner", "other"] else None
        return self.foods_get_recently_eaten_v1(meal=meal_arg)

    def foods_search(
        self,
        search_expression,
        page_number=None,
        max_results=None,
        region=None,
        language=None,
    ):
        """Conducts a search of the food database using the search expression specified.
        The results are paginated according to a zero-based "page" offset. Successive pages of results
        may be retrieved by specifying a starting page offset value. For instance, specifying a max_results
        of 10 and page_number of 4 will return results numbered 41-50.

        .. deprecated:: 1.0
            Use :meth:`foods_search_v1` for identical behavior or :meth:`foods_search_v5`
            for the current upstream version. This alias will be removed in v2.0.

        :param search_expression: term or phrase to search
        :type search_expression: str
        :param page_number: page set to return (default 0)
        :type page_number: int
        :param max_results: total results per page (default 20)
        :type max_results: int
        """
        warnings.warn(
            "Fatsecret.foods_search() is deprecated and will be removed in v2.0; "
            "use foods_search_v1() to preserve current behavior or foods_search_v5() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.foods_search_v1(
            search_expression,
            page_number=page_number,
            max_results=max_results,
            region=region,
            language=language,
        )

    def foods_autocomplete(
        self, expression, max_results=None, region=None, language=None
    ):
        """Returns a list of suggestions for the expression specified.

        .. deprecated:: 1.0
            Use :meth:`foods_autocomplete_v1` for identical behavior or
            :meth:`foods_autocomplete_v2` for the current upstream version.
            Note ``language`` is not supported by the underlying endpoint.
            This alias will be removed in v2.0.

        :param expression:
            Suggestions for the given expression is returned. E.G.: "chic" will return
            up to four of the best suggestions that contains "chic".

        :type expression: str
        :param page_number: page set to return (default 0)
        :type max_results: int
        """
        warnings.warn(
            "Fatsecret.foods_autocomplete() is deprecated and will be removed in v2.0; "
            "use foods_autocomplete_v1() to preserve current behavior or foods_autocomplete_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        del language  # preserved on signature for back-compat; v1 endpoint ignores it
        return self.foods_autocomplete_v1(
            expression, max_results=max_results, region=region
        )

    def food_entries_copy(self, from_date, to_date, meal=None):
        """
        Copies the food entries for a specified meal from a nominated date to a nominated date.

        .. deprecated:: 1.0
            Use :meth:`food_entries_copy_v1`. This alias will be removed in v2.0.

        :param from_date: The date to copy food entries from
        :type from_date: datetime.datetime
        :param to_date: The date to copy food entries to (default value is the current day).
        :type to_date: datetime.datetime
        :param meal: The type of meal to copy. Valid meal types are "breakfast", "lunch", "dinner" and "other"
            (default value is all).

        :type meal: str
        """
        warnings.warn(
            "Fatsecret.food_entries_copy() is deprecated and will be removed in v2.0; "
            "use food_entries_copy_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entries_copy_v1(from_date, to_date, meal=meal)

    def food_entries_copy_saved_meal(self, meal_id, meal, date=None):
        """Copies the food entries for a specified saved meal to a specified meal.

        .. deprecated:: 1.0
            Use :meth:`food_entries_copy_saved_meal_v1`. This alias will be removed in v2.0.

        :param meal_id: The ID of the saved meal
        :type meal_id: str
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        :param date: Day to copy meal to. (default value is the current day).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.food_entries_copy_saved_meal() is deprecated and will be removed in v2.0; "
            "use food_entries_copy_saved_meal_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entries_copy_saved_meal_v1(meal_id, meal, date=date)

    def food_entries_get(self, food_entry_id=None, date=None):
        """Returns saved food diary entries for the user according to the filter specified.
        This method can be used to return all food diary entries recorded on a nominated date or a single food
        diary entry with a nominated food_entry_id.
        :: You must specify either date or food_entry_id.

        .. deprecated:: 1.0
            Use :meth:`food_entries_get_v1` for identical behavior or
            :meth:`food_entries_get_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param food_entry_id: The ID of the food entry to retrieve. You must specify either date or food_entry_id.
        :type food_entry_id: str
        :param date: Day to filter food entries by (default value is the current day).
        :type date: datetime.datetmie
        """
        warnings.warn(
            "Fatsecret.food_entries_get() is deprecated and will be removed in v2.0; "
            "use food_entries_get_v1() to preserve current behavior or food_entries_get_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entries_get_v1(food_entry_id=food_entry_id, date=date)

    def food_entries_get_month(self, date=None):
        """Returns summary daily nutritional information for a user's food diary entries for the month specified.
        Use this call to display nutritional information to users about their food intake for a nominated month.

        .. deprecated:: 1.0
            Use :meth:`food_entries_get_month_v1` for identical behavior or
            :meth:`food_entries_get_month_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param date: Day in the month to return (default value is the current day to get current month).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.food_entries_get_month() is deprecated and will be removed in v2.0; "
            "use food_entries_get_month_v1() to preserve current behavior or "
            "food_entries_get_month_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entries_get_month_v1(date=date)

    def food_entry_create(
        self, food_id, food_entry_name, serving_id, number_of_units, meal, date=None
    ):
        """Records a food diary entry for the user according to the parameters specified.

        .. deprecated:: 1.0
            Use :meth:`food_entry_create_v1`. This alias will be removed in v2.0.

        :param food_id: The ID of the food eaten.
        :type food_id: str
        :param food_entry_name: The name of the food entry.
        :type food_entry_name: str
        :param serving_id: The ID of the serving
        :type serving_id: str
        :param number_of_units: The number of servings eaten.
        :type number_of_units: float
        :param meal: The type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        :param date: Day to create food entry on (default value is the current day).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.food_entry_create() is deprecated and will be removed in v2.0; "
            "use food_entry_create_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entry_create_v1(
            food_id, food_entry_name, serving_id, number_of_units, meal, date=date
        )

    def food_entry_delete(self, food_entry_id):
        """Deletes the specified food entry for the user.

        .. deprecated:: 1.0
            Use :meth:`food_entry_delete_v1`. This alias will be removed in v2.0.

        :param food_entry_id: The ID of the food entry to delete.
        :type food_entry_id: str
        """
        warnings.warn(
            "Fatsecret.food_entry_delete() is deprecated and will be removed in v2.0; "
            "use food_entry_delete_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entry_delete_v1(food_entry_id)

    def food_entry_edit(
        self, food_entry_id, entry_name=None, serving_id=None, num_units=None, meal=None
    ):
        """Adjusts the recorded values for a food diary entry.
        Note that the date of the entry may not be adjusted, however one or more of the other remaining
        properties - food_entry_name, serving_id, number_of_units, or meal may be altered. In order to shift
        the date for which a food diary entry was recorded the original entry must be deleted and a new entry recorded.

        .. deprecated:: 1.0
            Use :meth:`food_entry_edit_v1`. This alias will be removed in v2.0.

        :param food_entry_id: The ID of the food entry to edit.
        :type food_entry_id: str
        :param entry_name: The new name of the food entry.
        :type entry_name: str
        :param serving_id: The new ID of the serving to change to.
        :type serving_id: str
        :param num_units: The new number of servings eaten.
        :type num_units: float
        :param meal: The new type of meal eaten. Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meal: str
        """
        warnings.warn(
            "Fatsecret.food_entry_edit() is deprecated and will be removed in v2.0; "
            "use food_entry_edit_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.food_entry_edit_v1(
            food_entry_id,
            food_entry_name=entry_name,
            serving_id=serving_id,
            number_of_units=num_units,
            meal=meal,
        )

    # ========================= MEALS =========================

    def saved_meal_create(self, meal_name, meal_desc=None, meals=None):
        """
        Records a saved meal for the user according to the parameters specified.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_create_v1`. This alias will be removed in v2.0.

        :param meal_name: The name of the saved meal.
        :type meal_name: str
        :param meal_desc: A short description of the saved meal.
        :type meal_desc: str
        :param meals: A comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".

        :type meals: list
        """
        warnings.warn(
            "Fatsecret.saved_meal_create() is deprecated and will be removed in v2.0; "
            "use saved_meal_create_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        meals_str = ",".join(meals) if meals else None
        return self.saved_meal_create_v1(
            meal_name, saved_meal_description=meal_desc, meals=meals_str
        )

    def saved_meal_delete(self, meal_id):
        """
        Deletes the specified saved meal for the user.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_delete_v1`. This alias will be removed in v2.0.

        :param meal_id: The ID of the saved meal to delete.
        :type meal_id: str
        """
        warnings.warn(
            "Fatsecret.saved_meal_delete() is deprecated and will be removed in v2.0; "
            "use saved_meal_delete_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meal_delete_v1(meal_id)

    def saved_meal_edit(self, meal_id, new_name=None, meal_desc=None, meals=None):
        """
        Records a change to a user's saved meal.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_edit_v1`. This alias will be removed in v2.0.

        :param meal_id: The ID of the food entry to edit.
        :type meal_id: str
        :param new_name: The new name of the saved meal.
        :type new_name: str
        :param meal_desc: The new description of the saved meal.
        :type meal_desc: str
        :param meals: The new comma separated list of the types of meal this saved meal is suitable for.
            Valid meal types are "breakfast", "lunch", "dinner" and "other".
        :type meals: str
        """
        warnings.warn(
            "Fatsecret.saved_meal_edit() is deprecated and will be removed in v2.0; "
            "use saved_meal_edit_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        meals_str = ",".join(meals) if meals else None
        return self.saved_meal_edit_v1(
            meal_id,
            saved_meal_name=new_name,
            saved_meal_description=meal_desc,
            meals=meals_str,
        )

    def saved_meal_get(self, meal=None):
        """Returns saved meals for the authenticated user

        .. deprecated:: 1.0
            Use :meth:`saved_meals_get_v1` (note: plural — the name was corrected) for
            identical behavior or :meth:`saved_meals_get_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param meal: Filter result set to 'Breakfast', 'Lunch', 'Dinner', or 'Other'
        :type meal: str
        """
        warnings.warn(
            "Fatsecret.saved_meal_get() is deprecated and will be removed in v2.0; "
            "use saved_meals_get_v1() (plural) to preserve current behavior or "
            "saved_meals_get_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meals_get_v1(meal=meal)

    def saved_meal_item_add(
        self, meal_id, food_id, food_entry_name, serving_id, num_units
    ):
        """Adds a food to a user's saved meal according to the parameters specified.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_item_add_v1`. This alias will be removed in v2.0.

        :param meal_id: The ID of the saved meal.
        :type meal_id: str
        :param food_id: The ID of the food to add to the saved meal.
        :type food_id: str
        :param food_entry_name: The name of the food to add to the saved meal.
        :type food_entry_name: str
        :param serving_id: The ID of the serving of the food to add to the saved meal.
        :type serving_id: str
        :param num_units: The number of servings of the food to add to the saved meal.
        :type num_units: float
        """
        warnings.warn(
            "Fatsecret.saved_meal_item_add() is deprecated and will be removed in v2.0; "
            "use saved_meal_item_add_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meal_item_add_v1(
            meal_id, food_id, food_entry_name, serving_id, num_units
        )

    def saved_meal_item_delete(self, meal_item_id):
        """Deletes the specified saved meal item for the user.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_item_delete_v1`. This alias will be removed in v2.0.

        :param meal_item_id: The ID of the saved meal item to delete.
        :type meal_item_id: str
        """
        warnings.warn(
            "Fatsecret.saved_meal_item_delete() is deprecated and will be removed in v2.0; "
            "use saved_meal_item_delete_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meal_item_delete_v1(meal_item_id)

    def saved_meal_item_edit(self, meal_item_id, item_name=None, num_units=None):
        """Records a change to a user's saved meal item.
        Note that the serving_id of the saved meal item may not be adjusted, however one or more of the other
        remaining properties - saved_meal_item_name or number_of_units may be altered. In order to adjust a
        serving_id for which a saved_meal_item was recorded the original item must be deleted and a new item recorded.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_item_edit_v1`. This alias will be removed in v2.0.

        :param meal_item_id: The ID of the saved meal item to edit.
        :type meal_item_id: str
        :param item_name: The new name of the saved meal item.
        :type item_name: str
        :param num_units: The new number of servings of the saved meal item.
        :type num_units: float
        """
        warnings.warn(
            "Fatsecret.saved_meal_item_edit() is deprecated and will be removed in v2.0; "
            "use saved_meal_item_edit_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meal_item_edit_v1(
            meal_item_id,
            saved_meal_item_name=item_name,
            number_of_units=num_units,
        )

    def saved_meal_items_get(self, meal_id):
        """Returns saved meal items for a specified saved meal.

        .. deprecated:: 1.0
            Use :meth:`saved_meal_items_get_v1` for identical behavior or
            :meth:`saved_meal_items_get_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param meal_id: The ID of the saved meal to retrieve the saved_meal_items for.
        :type meal_id: str
        """
        warnings.warn(
            "Fatsecret.saved_meal_items_get() is deprecated and will be removed in v2.0; "
            "use saved_meal_items_get_v1() to preserve current behavior or "
            "saved_meal_items_get_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.saved_meal_items_get_v1(meal_id)

    # ========================= PROFILE =========================

    def profile_create(self, user_id=None):
        """Creates a new profile and returns the oauth_token and oauth_secret for the new profile.

        The token and secret returned by this method are persisted indefinitely and may be used in order to
        provide profile-specific information storage for users including food and exercise diaries and weight tracking.

        .. deprecated:: 1.0
            Use :meth:`profile_create_v1`. This alias will be removed in v2.0.

        :param user_id: You can set your own ID for the newly created profile if you do not wish to store the
            auth_token and auth_secret. Particularly useful if you are only using the FatSecret JavaScript API.
            Use profile.get_auth to retrieve auth_token and auth_secret.
        :type user_id: str
        """
        warnings.warn(
            "Fatsecret.profile_create() is deprecated and will be removed in v2.0; "
            "use profile_create_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.profile_create_v1(user_id=user_id)

    def profile_get(self):
        """Returns general status information for a nominated user.

        .. deprecated:: 1.0
            Use :meth:`profile_get_v1`. This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.profile_get() is deprecated and will be removed in v2.0; "
            "use profile_get_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.profile_get_v1()

    def profile_get_auth(self, user_id):
        """Returns the authentication information for a nominated user.

        .. deprecated:: 1.0
            Use :meth:`profile_get_auth_v1`. This alias will be removed in v2.0.

        :param user_id: The user_id specified in profile.create.
        :type user_id: str
        """
        warnings.warn(
            "Fatsecret.profile_get_auth() is deprecated and will be removed in v2.0; "
            "use profile_get_auth_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.profile_get_auth_v1(user_id=user_id)

    # ========================= RECIPES =========================

    def recipes_add_favorite(self, recipe_id):
        """Add a recipe to a user's favorite.

        .. deprecated:: 1.0
            Use :meth:`recipe_add_favorite_v1` (singular — the upstream method name was
            misspelled here as a plural). This alias will be removed in v2.0.

        :param recipe_id: The ID of the favorite recipe to add.
        :type recipe_id: str
        """
        warnings.warn(
            "Fatsecret.recipes_add_favorite() is deprecated and will be removed in v2.0; "
            "use recipe_add_favorite_v1() (singular — the legacy plural name was a typo).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipe_add_favorite_v1(recipe_id)

    def recipes_delete_favorite(self, recipe_id):
        """Delete a recipe to a user's favorite.

        .. deprecated:: 1.0
            Use :meth:`recipe_delete_favorite_v1` (singular — the upstream method name was
            misspelled here as a plural). This alias will be removed in v2.0.

        :param recipe_id: The ID of the favorite recipe to delete.
        :type recipe_id: str
        """
        warnings.warn(
            "Fatsecret.recipes_delete_favorite() is deprecated and will be removed in v2.0; "
            "use recipe_delete_favorite_v1() (singular — the legacy plural name was a typo).",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipe_delete_favorite_v1(recipe_id)

    def recipe_get(self, recipe_id):
        """Returns detailed information for the specified recipe.

        .. deprecated:: 1.0
            Use :meth:`recipe_get_v1` for identical behavior or :meth:`recipe_get_v2`
            for the current upstream version. This alias will be removed in v2.0.

        :param recipe_id: Fatsecret ID of desired recipe
        :type recipe_id: str
        """
        warnings.warn(
            "Fatsecret.recipe_get() is deprecated and will be removed in v2.0; "
            "use recipe_get_v1() to preserve current behavior or recipe_get_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipe_get_v1(recipe_id)

    def recipes_get_favorites(self):
        """Returns the favorite recipes for the specified user.

        .. deprecated:: 1.0
            Use :meth:`recipes_get_favorites_v1` for identical behavior or
            :meth:`recipes_get_favorites_v2` for the current upstream version.
            This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.recipes_get_favorites() is deprecated and will be removed in v2.0; "
            "use recipes_get_favorites_v1() to preserve current behavior or "
            "recipes_get_favorites_v2() for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipes_get_favorites_v1()

    def recipes_search(
        self, search_expression, recipe_type=None, page_number=None, max_results=None
    ):
        """Conducts a search of the recipe database using the search expression specified.

        The results are paginated according to a zero-based "page" offset. Successive pages of results may be
        retrieved by specifying a starting page offset value. For instance, specifying a max_results of 10 and
        page_number of 4 will return results numbered 41-50.

        .. deprecated:: 1.0
            Use :meth:`recipes_search_v1` for identical behavior or :meth:`recipes_search_v3`
            for the current upstream version. This alias will be removed in v2.0.

        :param search_expression: phrase to search on
        :type search_expression: str
        :param recipe_type: type of recipe to filter
        :type recipe_type: str
        :param page_number: result page to return (default 0)
        :type page_number: int
        :param max_results: total results per page to return (default 20)
        :type max_results: int
        """
        warnings.warn(
            "Fatsecret.recipes_search() is deprecated and will be removed in v2.0; "
            "use recipes_search_v1() to preserve current behavior or recipes_search_v3() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipes_search_v1(
            search_expression=search_expression,
            recipe_type=recipe_type,
            page_number=page_number,
            max_results=max_results,
        )

    def recipe_types_get(self):
        """This is a utility method, returning the full list of all supported recipe type names.

        .. deprecated:: 1.0
            Use :meth:`recipe_types_get_v1` for identical behavior or
            :meth:`recipe_types_get_v2` for the current upstream version.
            This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.recipe_types_get() is deprecated and will be removed in v2.0; "
            "use recipe_types_get_v1() to preserve current behavior or recipe_types_get_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.recipe_types_get_v1()

    # ========================= WEIGHT =========================

    def weight_update(
        self,
        current_weight_kg,
        date=None,
        weight_type="kg",
        height_type="cm",
        goal_weight_kg=None,
        current_height_cm=None,
        comment=None,
    ):
        """Records a user's weight for a nominated date.

        First time weigh-ins require the goal_weight_kg and current_height_cm parameters.

        :param current_weight_kg: The current weight of the user in kilograms.
        :type current_weight_kg: float
        :param date: Day to for weight record (default value is the current day).
        :type date: datetime.datetime
        :param weight_type: The weight measurement type for this user profile. Valid types are "kg" and "lb"
        :type weight_type: str
        :param height_type: The height measurement type for this user profile. Valid types are "cm" and "inch"
        :type height_type: str
        :param goal_weight_kg: The goal weight of the user in kilograms. This is required for the first weigh-in.
        :type goal_weight_kg: float
        :param current_height_cm: The current height of the user in centimetres. This is required for the first
            weigh-in. You can only set this for the first time (subsequent updates will not change a user's height)
        :type current_height_cm: float
        :param comment: A comment for this weigh-in.
        :type comment: str

        .. deprecated:: 1.0
            Use :meth:`weight_update_v1`. This alias will be removed in v2.0.
        """
        warnings.warn(
            "Fatsecret.weight_update() is deprecated and will be removed in v2.0; "
            "use weight_update_v1().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.weight_update_v1(
            current_weight_kg,
            date=date,
            weight_type=weight_type,
            height_type=height_type,
            goal_weight_kg=goal_weight_kg,
            current_height_cm=current_height_cm,
            comment=comment,
        )

    def weights_get_month(self, date=None):
        """Returns the recorded weights for a user for the month specified. Use this call to display a user's
        weight chart or log of weight changes for a nominated month.

        .. deprecated:: 1.0
            Use :meth:`weights_get_month_v1` for identical behavior or
            :meth:`weights_get_month_v2` for the current upstream version.
            This alias will be removed in v2.0.

        :param date: Day within month to return (default value is the current day for the current month).
        :type date: datetime.datetime
        """
        warnings.warn(
            "Fatsecret.weights_get_month() is deprecated and will be removed in v2.0; "
            "use weights_get_month_v1() to preserve current behavior or weights_get_month_v2() "
            "for the latest upstream version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.weights_get_month_v1(date=date)

    # ========================= VERSIONED METHODS (v1.0+) =========================
    # Auto-added in v1.0 to cover every (method, version) pair documented at
    # platform.fatsecret.com/docs. Source of truth: docs/api-spec/raw/*.yaml.
    # See docs/MIGRATION.md for naming conventions and docs/DECISIONS.md for design rationale.

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

    # ------------------------- Foods: foods.search -------------------------

    def foods_search_v1(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        generic_description: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v1. Lightweight result set (no nested servings).

        Region/language are Premier-exclusive on v1.
        """
        params = {"method": "foods.search", "search_expression": search_expression}
        self._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("generic_description", generic_description),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "foods", list_key="food")

    def foods_search_v2(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v2 (DEPRECATED upstream). Returns nested servings + nutrition. Premier."""
        params = {"method": "foods.search.v2", "search_expression": search_expression}
        self._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "foods_search", "results", list_key="food")

    def foods_search_v3(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v3 (DEPRECATED upstream). Adds include_food_images and include_food_attributes. Premier."""
        params = {"method": "foods.search.v3", "search_expression": search_expression}
        self._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "foods_search", "results", list_key="food")

    def foods_search_v4(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v4 (DEPRECATED upstream). Brand foods include derived 100g/100ml servings. Premier."""
        params = {"method": "foods.search.v4", "search_expression": search_expression}
        self._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "foods_search", "results", list_key="food")

    def foods_search_v5(
        self,
        search_expression: str,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        food_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """foods.search v5 (current). Adds `food_type` filter ('none'/'generic'/'brand'). Premier."""
        params = {"method": "foods.search.v5", "search_expression": search_expression}
        self._set_optional(
            params,
            [
                ("page_number", page_number),
                ("max_results", max_results),
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("food_type", food_type),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "foods_search", "results", list_key="food")

    # ------------------------- Foods: food.get -------------------------

    def food_get_v1(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v1 (DEPRECATED upstream). Vitamins A/C, calcium, iron reported as %DV."""
        params = {"method": "food.get", "food_id": food_id}
        self._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food")

    # food_get_v2: existing legacy method (lines ~679-692 above) already targets food.get.v2.
    # Per DECISIONS.md, it is preserved as-is; the v2 (method, version) pair is therefore covered.

    def food_get_v3(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v3 (DEPRECATED upstream). Schema near-identical to v2."""
        params = {"method": "food.get.v3", "food_id": food_id}
        self._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food")

    def food_get_v4(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v4 (DEPRECATED upstream). Adds food_images and food_attributes (allergens, preferences)."""
        params = {"method": "food.get.v4", "food_id": food_id}
        self._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food")

    def food_get_v5(
        self,
        food_id: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.get v5 (current). Brand foods get derived 100g/100ml servings with serving_id=0."""
        params = {"method": "food.get.v5", "food_id": food_id}
        self._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food")

    # ------------------------- Foods: autocomplete -------------------------

    def foods_autocomplete_v1(
        self,
        expression: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
    ) -> list:
        """foods.autocomplete v1 (DEPRECATED upstream). Premier-only."""
        params = {"method": "foods.autocomplete", "expression": expression}
        self._set_optional(params, [("max_results", max_results), ("region", region)])
        payload = self._call(params)
        return self._unwrap(payload, "suggestions", list_key="suggestion")

    def foods_autocomplete_v2(
        self,
        expression: str,
        max_results: Optional[int] = None,
        region: Optional[str] = None,
    ) -> list:
        """foods.autocomplete v2 (current). Premier-only."""
        params = {"method": "foods.autocomplete.v2", "expression": expression}
        self._set_optional(params, [("max_results", max_results), ("region", region)])
        payload = self._call(params)
        return self._unwrap(payload, "suggestions", list_key="suggestion")

    # ------------------------- Foods: find_id_for_barcode -------------------------

    def food_find_id_for_barcode_v1(
        self,
        barcode: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.find_id_for_barcode v1. Premier (`barcode` scope). Returns food_id (0 if no match)."""
        params = {"method": "food.find_id_for_barcode", "barcode": barcode}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "food_id")

    def food_find_id_for_barcode_v2(
        self,
        barcode: str,
        include_sub_categories: Optional[bool] = None,
        include_food_images: Optional[bool] = None,
        include_food_attributes: Optional[bool] = None,
        flag_default_serving: Optional[bool] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """food.find_id_for_barcode v2. Returns full food record. Premier (`barcode` scope)."""
        params = {"method": "food.find_id_for_barcode.v2", "barcode": barcode}
        self._set_optional(
            params,
            [
                ("include_sub_categories", include_sub_categories),
                ("include_food_images", include_food_images),
                ("include_food_attributes", include_food_attributes),
                ("flag_default_serving", flag_default_serving),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food")

    # ------------------------- Food Classification: brands -------------------------

    def food_brands_get_v1(
        self,
        starts_with: str,
        brand_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_brands.get v1 (DEPRECATED upstream). Premier."""
        params = {"method": "food_brands.get", "starts_with": starts_with}
        self._set_optional(
            params,
            [("brand_type", brand_type), ("region", region), ("language", language)],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food_brands", list_key="food_brand")

    def food_brands_get_v2(
        self,
        starts_with: str,
        brand_type: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_brands.get v2 (current). Premier."""
        params = {"method": "food_brands.get.v2", "starts_with": starts_with}
        self._set_optional(
            params,
            [("brand_type", brand_type), ("region", region), ("language", language)],
        )
        payload = self._call(params)
        return self._unwrap(payload, "food_brands", list_key="food_brand")

    # ------------------------- Food Classification: categories -------------------------

    def food_categories_get_v1(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """food_categories.get v1 (DEPRECATED upstream). Premier."""
        params = {"method": "food_categories.get"}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "food_categories", list_key="food_category")

    def food_categories_get_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """food_categories.get v2 (current). Premier."""
        params = {"method": "food_categories.get.v2"}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "food_categories", list_key="food_category")

    # ------------------------- Food Classification: sub-categories -------------------------

    def food_sub_categories_get_v1(
        self,
        food_category_id: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_sub_categories.get v1 (DEPRECATED upstream). Premier."""
        params = {
            "method": "food_sub_categories.get",
            "food_category_id": food_category_id,
        }
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(
            payload, "food_sub_categories", list_key="food_sub_category"
        )

    def food_sub_categories_get_v2(
        self,
        food_category_id: str,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """food_sub_categories.get v2 (current). Premier."""
        params = {
            "method": "food_sub_categories.get.v2",
            "food_category_id": food_category_id,
        }
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(
            payload, "food_sub_categories", list_key="food_sub_category"
        )

    # ------------------------- Recipes: recipe.get -------------------------

    def recipe_get_v1(self, recipe_id: str, region: Optional[str] = None) -> dict:
        """recipe.get v1 (DEPRECATED upstream)."""
        params = {"method": "recipe.get", "recipe_id": recipe_id}
        self._set_optional(params, [("region", region)])
        payload = self._call(params)
        return self._unwrap(payload, "recipe")

    def recipe_get_v2(self, recipe_id: str, region: Optional[str] = None) -> dict:
        """recipe.get v2 (current). Adds grams_per_portion."""
        params = {"method": "recipe.get.v2", "recipe_id": recipe_id}
        self._set_optional(params, [("region", region)])
        payload = self._call(params)
        return self._unwrap(payload, "recipe")

    # ------------------------- Recipes: recipes.search -------------------------

    def recipes_search_v1(
        self,
        search_expression: Optional[str] = None,
        recipe_type: Optional[str] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
    ) -> list:
        """recipes.search v1 (DEPRECATED upstream)."""
        params: dict = {"method": "recipes.search"}
        self._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("recipe_type", recipe_type),
                ("page_number", page_number),
                ("max_results", max_results),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "recipes", list_key="recipe")

    def recipes_search_v2(
        self,
        search_expression: Optional[str] = None,
        must_have_images: Optional[bool] = None,
        calories_from: Optional[int] = None,
        calories_to: Optional[int] = None,
        carb_percentage_from: Optional[int] = None,
        carb_percentage_to: Optional[int] = None,
        protein_percentage_from: Optional[int] = None,
        protein_percentage_to: Optional[int] = None,
        fat_percentage_from: Optional[int] = None,
        fat_percentage_to: Optional[int] = None,
        prep_time_from: Optional[int] = None,
        prep_time_to: Optional[int] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        sort_by: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list:
        """recipes.search v2 (DEPRECATED upstream). Adds nutritional/time filters."""
        params: dict = {"method": "recipes.search.v2"}
        self._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("must_have_images", must_have_images),
                ("calories.from", calories_from),
                ("calories.to", calories_to),
                ("carb_percentage.from", carb_percentage_from),
                ("carb_percentage.to", carb_percentage_to),
                ("protein_percentage.from", protein_percentage_from),
                ("protein_percentage.to", protein_percentage_to),
                ("fat_percentage.from", fat_percentage_from),
                ("fat_percentage.to", fat_percentage_to),
                ("prep_time.from", prep_time_from),
                ("prep_time.to", prep_time_to),
                ("page_number", page_number),
                ("max_results", max_results),
                ("sort_by", sort_by),
                ("region", region),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "recipes", list_key="recipe")

    def recipes_search_v3(
        self,
        search_expression: Optional[str] = None,
        recipe_types: Optional[str] = None,
        recipe_types_matchall: Optional[bool] = None,
        must_have_images: Optional[bool] = None,
        calories_from: Optional[int] = None,
        calories_to: Optional[int] = None,
        carb_percentage_from: Optional[int] = None,
        carb_percentage_to: Optional[int] = None,
        protein_percentage_from: Optional[int] = None,
        protein_percentage_to: Optional[int] = None,
        fat_percentage_from: Optional[int] = None,
        fat_percentage_to: Optional[int] = None,
        prep_time_from: Optional[int] = None,
        prep_time_to: Optional[int] = None,
        page_number: Optional[int] = None,
        max_results: Optional[int] = None,
        sort_by: Optional[str] = None,
        region: Optional[str] = None,
    ) -> list:
        """recipes.search v3 (current). Adds recipe_types comma-list + matchall."""
        params: dict = {"method": "recipes.search.v3"}
        self._set_optional(
            params,
            [
                ("search_expression", search_expression),
                ("recipe_types", recipe_types),
                ("recipe_types_matchall", recipe_types_matchall),
                ("must_have_images", must_have_images),
                ("calories.from", calories_from),
                ("calories.to", calories_to),
                ("carb_percentage.from", carb_percentage_from),
                ("carb_percentage.to", carb_percentage_to),
                ("protein_percentage.from", protein_percentage_from),
                ("protein_percentage.to", protein_percentage_to),
                ("fat_percentage.from", fat_percentage_from),
                ("fat_percentage.to", fat_percentage_to),
                ("prep_time.from", prep_time_from),
                ("prep_time.to", prep_time_to),
                ("page_number", page_number),
                ("max_results", max_results),
                ("sort_by", sort_by),
                ("region", region),
            ],
        )
        payload = self._call(params)
        return self._unwrap(payload, "recipes", list_key="recipe")

    # ------------------------- Recipes: recipe_types.get -------------------------

    def recipe_types_get_v1(self) -> list:
        """recipe_types.get v1 (DEPRECATED upstream)."""
        payload = self._call({"method": "recipe_types.get"})
        return self._unwrap(payload, "recipe_types", list_key="recipe_type")

    def recipe_types_get_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """recipe_types.get v2 (current). Region/language are Premier-exclusive."""
        params = {"method": "recipe_types.get.v2"}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "recipe_types", list_key="recipe_type")

    # ------------------------- Recipes: favorites -------------------------

    def recipe_add_favorite_v1(self, recipe_id: str) -> Union[bool, Any]:
        """recipe.add_favorite v1. Fixes the legacy plural-typo bug (uses singular `recipe.add_favorite`)."""
        payload = self._call(
            {"method": "recipe.add_favorite", "recipe_id": recipe_id}, method="POST"
        )
        return self._mutator_success(payload)

    def recipe_delete_favorite_v1(self, recipe_id: str) -> Union[bool, Any]:
        """recipe.delete_favorite v1. Fixes the legacy plural-typo bug."""
        payload = self._call(
            {"method": "recipe.delete_favorite", "recipe_id": recipe_id},
            method="DELETE",
        )
        return self._mutator_success(payload)

    def recipes_get_favorites_v1(self) -> list:
        """recipes.get_favorites v1 (DEPRECATED upstream). api_method_param: recipe.get_favorites."""
        payload = self._call({"method": "recipe.get_favorites"})
        return self._unwrap(payload, "recipes", list_key="recipe")

    def recipes_get_favorites_v2(self) -> list:
        """recipes.get_favorites v2 (current). api_method_param: recipe.get_favorites.v2."""
        payload = self._call({"method": "recipe.get_favorites.v2"})
        return self._unwrap(payload, "recipes", list_key="recipe")

    # ------------------------- Profile-Foods: food.create -------------------------

    def food_create_v1(
        self,
        brand_name: str,
        food_name: str,
        serving_size: str,
        calories: float,
        fat: float,
        carbohydrate: float,
        protein: float,
        brand_type: Optional[str] = None,
        serving_amount: Optional[str] = None,
        serving_amount_unit: Optional[str] = None,
        calories_from_fat: Optional[float] = None,
        saturated_fat: Optional[float] = None,
        polyunsaturated_fat: Optional[float] = None,
        monounsaturated_fat: Optional[float] = None,
        trans_fat: Optional[float] = None,
        cholesterol: Optional[float] = None,
        sodium: Optional[float] = None,
        potassium: Optional[float] = None,
        fiber: Optional[float] = None,
        sugar: Optional[float] = None,
        other_carbohydrate: Optional[float] = None,
        vitamin_a: Optional[float] = None,
        vitamin_c: Optional[float] = None,
        calcium: Optional[float] = None,
        iron: Optional[float] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.create v1 (DEPRECATED upstream). Premier-exclusive. OAuth1 only.

        v1 takes vitamin_a/c, calcium, iron as %DV.
        """
        params = {
            "method": "food.create",
            "brand_name": brand_name,
            "food_name": food_name,
            "serving_size": serving_size,
            "calories": calories,
            "fat": fat,
            "carbohydrate": carbohydrate,
            "protein": protein,
        }
        self._set_optional(
            params,
            [
                ("brand_type", brand_type),
                ("serving_amount", serving_amount),
                ("serving_amount_unit", serving_amount_unit),
                ("calories_from_fat", calories_from_fat),
                ("saturated_fat", saturated_fat),
                ("polyunsaturated_fat", polyunsaturated_fat),
                ("monounsaturated_fat", monounsaturated_fat),
                ("trans_fat", trans_fat),
                ("cholesterol", cholesterol),
                ("sodium", sodium),
                ("potassium", potassium),
                ("fiber", fiber),
                ("sugar", sugar),
                ("other_carbohydrate", other_carbohydrate),
                ("vitamin_a", vitamin_a),
                ("vitamin_c", vitamin_c),
                ("calcium", calcium),
                ("iron", iron),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params, method="POST")
        return self._unwrap(payload, "food_id")

    def food_create_v2(
        self,
        brand_name: str,
        food_name: str,
        serving_size: str,
        calories: float,
        fat: float,
        carbohydrate: float,
        protein: float,
        brand_type: Optional[str] = None,
        serving_amount: Optional[str] = None,
        serving_amount_unit: Optional[str] = None,
        calories_from_fat: Optional[float] = None,
        saturated_fat: Optional[float] = None,
        polyunsaturated_fat: Optional[float] = None,
        monounsaturated_fat: Optional[float] = None,
        trans_fat: Optional[float] = None,
        cholesterol: Optional[float] = None,
        sodium: Optional[float] = None,
        potassium: Optional[float] = None,
        fiber: Optional[float] = None,
        sugar: Optional[float] = None,
        added_sugars: Optional[float] = None,
        vitamin_d: Optional[float] = None,
        vitamin_a: Optional[float] = None,
        vitamin_c: Optional[float] = None,
        calcium: Optional[float] = None,
        iron: Optional[float] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Any:
        """food.create v2 (current). Premier-exclusive. OAuth1 only.

        v2 takes raw nutrient values; adds added_sugars and vitamin_d.
        """
        params = {
            "method": "food.create.v2",
            "brand_name": brand_name,
            "food_name": food_name,
            "serving_size": serving_size,
            "calories": calories,
            "fat": fat,
            "carbohydrate": carbohydrate,
            "protein": protein,
        }
        self._set_optional(
            params,
            [
                ("brand_type", brand_type),
                ("serving_amount", serving_amount),
                ("serving_amount_unit", serving_amount_unit),
                ("calories_from_fat", calories_from_fat),
                ("saturated_fat", saturated_fat),
                ("polyunsaturated_fat", polyunsaturated_fat),
                ("monounsaturated_fat", monounsaturated_fat),
                ("trans_fat", trans_fat),
                ("cholesterol", cholesterol),
                ("sodium", sodium),
                ("potassium", potassium),
                ("fiber", fiber),
                ("sugar", sugar),
                ("added_sugars", added_sugars),
                ("vitamin_d", vitamin_d),
                ("vitamin_a", vitamin_a),
                ("vitamin_c", vitamin_c),
                ("calcium", calcium),
                ("iron", iron),
                ("region", region),
                ("language", language),
            ],
        )
        payload = self._call(params, method="POST")
        return self._unwrap(payload, "food_id")

    # ------------------------- Profile-Foods: favorites/eaten -------------------------

    def food_add_favorite_v1(
        self,
        food_id: str,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """food.add_favorite v1."""
        params = {"method": "food.add_favorite", "food_id": food_id}
        self._set_optional(
            params, [("serving_id", serving_id), ("number_of_units", number_of_units)]
        )
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    def food_delete_favorite_v1(
        self,
        food_id: str,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """food.delete_favorite v1."""
        params = {"method": "food.delete_favorite", "food_id": food_id}
        self._set_optional(
            params, [("serving_id", serving_id), ("number_of_units", number_of_units)]
        )
        payload = self._call(params, method="DELETE")
        return self._mutator_success(payload)

    def foods_get_favorites_v1(self) -> list:
        """foods.get_favorites v1 (DEPRECATED upstream)."""
        payload = self._call({"method": "foods.get_favorites"})
        return self._unwrap(payload, "foods", list_key="food")

    def foods_get_favorites_v2(self) -> list:
        """foods.get_favorites v2 (current)."""
        payload = self._call({"method": "foods.get_favorites.v2"})
        return self._unwrap(payload, "foods", list_key="food")

    def foods_get_most_eaten_v1(self, meal: Optional[str] = None) -> list:
        """foods.get_most_eaten v1 (DEPRECATED upstream)."""
        params = {"method": "foods.get_most_eaten"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "foods", list_key="food")

    def foods_get_most_eaten_v2(self, meal: Optional[str] = None) -> list:
        """foods.get_most_eaten v2 (current)."""
        params = {"method": "foods.get_most_eaten.v2"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "foods", list_key="food")

    def foods_get_recently_eaten_v1(self, meal: Optional[str] = None) -> list:
        """foods.get_recently_eaten v1 (DEPRECATED upstream)."""
        params = {"method": "foods.get_recently_eaten"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "foods", list_key="food")

    def foods_get_recently_eaten_v2(self, meal: Optional[str] = None) -> list:
        """foods.get_recently_eaten v2 (current). Premier per spec."""
        params = {"method": "foods.get_recently_eaten.v2"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "foods", list_key="food")

    # ------------------------- Saved Meals -------------------------

    def saved_meal_create_v1(
        self,
        saved_meal_name: str,
        saved_meal_description: Optional[str] = None,
        meals: Optional[str] = None,
    ) -> Any:
        """saved_meal.create v1."""
        params = {"method": "saved_meal.create", "saved_meal_name": saved_meal_name}
        self._set_optional(
            params,
            [("saved_meal_description", saved_meal_description), ("meals", meals)],
        )
        payload = self._call(params, method="POST")
        return self._unwrap(payload, "saved_meal_id")

    def saved_meal_edit_v1(
        self,
        saved_meal_id: str,
        saved_meal_name: Optional[str] = None,
        saved_meal_description: Optional[str] = None,
        meals: Optional[str] = None,
    ) -> Union[bool, Any]:
        """saved_meal.edit v1."""
        params = {"method": "saved_meal.edit", "saved_meal_id": saved_meal_id}
        self._set_optional(
            params,
            [
                ("saved_meal_name", saved_meal_name),
                ("saved_meal_description", saved_meal_description),
                ("meals", meals),
            ],
        )
        payload = self._call(params, method="PUT")
        return self._mutator_success(payload)

    def saved_meal_delete_v1(self, saved_meal_id: str) -> Union[bool, Any]:
        """saved_meal.delete v1."""
        payload = self._call(
            {"method": "saved_meal.delete", "saved_meal_id": saved_meal_id},
            method="DELETE",
        )
        return self._mutator_success(payload)

    def saved_meals_get_v1(self, meal: Optional[str] = None) -> list:
        """saved_meals.get v1 (DEPRECATED upstream)."""
        params = {"method": "saved_meals.get"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "saved_meals", list_key="saved_meal")

    def saved_meals_get_v2(self, meal: Optional[str] = None) -> list:
        """saved_meals.get v2 (current)."""
        params = {"method": "saved_meals.get.v2"}
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params)
        return self._unwrap(payload, "saved_meals", list_key="saved_meal")

    def saved_meal_item_add_v1(
        self,
        saved_meal_id: str,
        food_id: str,
        saved_meal_item_name: str,
        serving_id: str,
        number_of_units: float,
    ) -> Any:
        """saved_meal_item.add v1."""
        params = {
            "method": "saved_meal_item.add",
            "saved_meal_id": saved_meal_id,
            "food_id": food_id,
            "saved_meal_item_name": saved_meal_item_name,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
        }
        payload = self._call(params, method="POST")
        return self._unwrap(payload, "saved_meal_item_id")

    def saved_meal_item_edit_v1(
        self,
        saved_meal_item_id: str,
        saved_meal_item_name: Optional[str] = None,
        number_of_units: Optional[float] = None,
    ) -> Union[bool, Any]:
        """saved_meal_item.edit v1."""
        params = {
            "method": "saved_meal_item.edit",
            "saved_meal_item_id": saved_meal_item_id,
        }
        self._set_optional(
            params,
            [
                ("saved_meal_item_name", saved_meal_item_name),
                ("number_of_units", number_of_units),
            ],
        )
        payload = self._call(params, method="PUT")
        return self._mutator_success(payload)

    def saved_meal_item_delete_v1(self, saved_meal_item_id: str) -> Union[bool, Any]:
        """saved_meal_item.delete v1."""
        payload = self._call(
            {
                "method": "saved_meal_item.delete",
                "saved_meal_item_id": saved_meal_item_id,
            },
            method="DELETE",
        )
        return self._mutator_success(payload)

    def saved_meal_items_get_v1(self, saved_meal_id: str) -> list:
        """saved_meal_items.get v1 (DEPRECATED upstream)."""
        payload = self._call(
            {"method": "saved_meal_items.get", "saved_meal_id": saved_meal_id}
        )
        return self._unwrap(payload, "saved_meal_items", list_key="saved_meal_item")

    def saved_meal_items_get_v2(self, saved_meal_id: str) -> list:
        """saved_meal_items.get v2 (current)."""
        payload = self._call(
            {"method": "saved_meal_items.get.v2", "saved_meal_id": saved_meal_id}
        )
        return self._unwrap(payload, "saved_meal_items", list_key="saved_meal_item")

    # ------------------------- Food Diary -------------------------

    def food_entry_create_v1(
        self,
        food_id: str,
        food_entry_name: str,
        serving_id: str,
        number_of_units: float,
        meal: str,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entry.create v1."""
        params = {
            "method": "food_entry.create",
            "food_id": food_id,
            "food_entry_name": food_entry_name,
            "serving_id": serving_id,
            "number_of_units": number_of_units,
            "meal": meal,
        }
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params, method="POST")
        return self._unwrap(payload, "food_entries", list_key="food_entry")

    def food_entry_edit_v1(
        self,
        food_entry_id: str,
        food_entry_name: Optional[str] = None,
        serving_id: Optional[str] = None,
        number_of_units: Optional[float] = None,
        meal: Optional[str] = None,
    ) -> Union[bool, Any]:
        """food_entry.edit v1."""
        params = {"method": "food_entry.edit", "food_entry_id": food_entry_id}
        self._set_optional(
            params,
            [
                ("food_entry_name", food_entry_name),
                ("serving_id", serving_id),
                ("number_of_units", number_of_units),
                ("meal", meal),
            ],
        )
        payload = self._call(params, method="PUT")
        return self._mutator_success(payload)

    def food_entry_delete_v1(self, food_entry_id: str) -> Union[bool, Any]:
        """food_entry.delete v1."""
        payload = self._call(
            {"method": "food_entry.delete", "food_entry_id": food_entry_id},
            method="DELETE",
        )
        return self._mutator_success(payload)

    def food_entries_get_v1(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get v1 (DEPRECATED upstream). Pass either food_entry_id or date."""
        if food_entry_id is None and date is None:
            return []
        params: dict = {"method": "food_entries.get"}
        if food_entry_id is not None:
            params["food_entry_id"] = food_entry_id
        else:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "food_entries", list_key="food_entry")

    def food_entries_get_v2(
        self,
        food_entry_id: Optional[str] = None,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get v2 (current). Pass either food_entry_id or date."""
        if food_entry_id is None and date is None:
            return []
        params: dict = {"method": "food_entries.get.v2"}
        if food_entry_id is not None:
            params["food_entry_id"] = food_entry_id
        else:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "food_entries", list_key="food_entry")

    def food_entries_get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "food_entries.get_month"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def food_entries_get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """food_entries.get_month v2 (current)."""
        params: dict = {"method": "food_entries.get_month.v2"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def food_entries_copy_v1(
        self,
        from_date: Union[datetime.datetime, datetime.date, int, float],
        to_date: Union[datetime.datetime, datetime.date, int, float],
        meal: Optional[str] = None,
    ) -> Union[bool, Any]:
        """food_entries.copy v1."""
        params = {
            "method": "food_entries.copy",
            "from_date": self.unix_time_v2(from_date),
            "to_date": self.unix_time_v2(to_date),
        }
        self._set_optional(params, [("meal", meal)])
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    def food_entries_copy_saved_meal_v1(
        self,
        saved_meal_id: str,
        meal: str,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """food_entries.copy_saved_meal v1."""
        params = {
            "method": "food_entries.copy_saved_meal",
            "saved_meal_id": saved_meal_id,
            "meal": meal,
        }
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    # ------------------------- Exercise / Weight / Profile -------------------------

    def exercises_get_v1(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """exercises.get v1 (DEPRECATED upstream)."""
        params = {"method": "exercises.get"}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "exercise_types", list_key="exercise")

    def exercises_get_v2(
        self, region: Optional[str] = None, language: Optional[str] = None
    ) -> list:
        """exercises.get v2 (current). Region/language are Premier-exclusive."""
        params = {"method": "exercises.get.v2"}
        self._set_optional(params, [("region", region), ("language", language)])
        payload = self._call(params)
        return self._unwrap(payload, "exercise_types", list_key="exercise")

    def exercise_entry_edit_v1(
        self,
        shift_to_id: str,
        shift_from_id: str,
        minutes: int,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
        shift_to_name: Optional[str] = None,
        shift_from_name: Optional[str] = None,
        kcal: Optional[int] = None,
    ) -> Union[bool, Any]:
        """exercise_entry.edit v1. Shifts time between activities while maintaining 24h balance."""
        params = {
            "method": "exercise_entry.edit",
            "shift_to_id": shift_to_id,
            "shift_from_id": shift_from_id,
            "minutes": minutes,
        }
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        self._set_optional(
            params,
            [
                ("shift_to_name", shift_to_name),
                ("shift_from_name", shift_from_name),
                ("kcal", kcal),
            ],
        )
        payload = self._call(params, method="PUT")
        return self._mutator_success(payload)

    def exercise_entries_get_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get v1 (DEPRECATED upstream)."""
        params: dict = {"method": "exercise_entries.get"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "exercise_entries", list_key="exercise_entry")

    def exercise_entries_get_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get v2 (current)."""
        params: dict = {"method": "exercise_entries.get.v2"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "exercise_entries", list_key="exercise_entry")

    def exercise_entries_get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "exercise_entries.get_month"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def exercise_entries_get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """exercise_entries.get_month v2 (current)."""
        params: dict = {"method": "exercise_entries.get_month.v2"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def exercise_entries_commit_day_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """exercise_entries.commit_day v1."""
        params: dict = {"method": "exercise_entries.commit_day"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    def exercise_entries_save_template_v1(
        self,
        days: int,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> Union[bool, Any]:
        """exercise_entries.save_template v1. Fixes the legacy bug that hit `exercise_entries.get_month`."""
        params = {"method": "exercise_entries.save_template", "days": int(days)}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    def weight_update_v1(
        self,
        current_weight_kg: float,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
        weight_type: Optional[str] = None,
        height_type: Optional[str] = None,
        goal_weight_kg: Optional[float] = None,
        current_height_cm: Optional[float] = None,
        comment: Optional[str] = None,
    ) -> Union[bool, Any]:
        """weight.update v1. First-time entries require goal_weight_kg and current_height_cm."""
        params = {"method": "weight.update", "current_weight_kg": current_weight_kg}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        self._set_optional(
            params,
            [
                ("weight_type", weight_type),
                ("height_type", height_type),
                ("goal_weight_kg", goal_weight_kg),
                ("current_height_cm", current_height_cm),
                ("comment", comment),
            ],
        )
        payload = self._call(params, method="POST")
        return self._mutator_success(payload)

    def weights_get_month_v1(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """weights.get_month v1 (DEPRECATED upstream)."""
        params: dict = {"method": "weights.get_month"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def weights_get_month_v2(
        self,
        date: Optional[Union[datetime.datetime, datetime.date, int, float]] = None,
    ) -> list:
        """weights.get_month v2 (current)."""
        params: dict = {"method": "weights.get_month.v2"}
        if date is not None:
            params["date"] = self.unix_time_v2(date)
        payload = self._call(params)
        return self._unwrap(payload, "month", list_key="day")

    def profile_create_v1(self, user_id: Optional[str] = None) -> Any:
        """profile.create v1. Returns (auth_token, auth_secret) when user_id is supplied."""
        params: dict = {"method": "profile.create"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._call(params, method="POST")
        profile = self._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile

    def profile_get_v1(self) -> dict:
        """profile.get v1. Returns the user's profile dict."""
        payload = self._call({"method": "profile.get"})
        return self._unwrap(payload, "profile")

    def profile_get_auth_v1(self, user_id: Optional[str] = None) -> Any:
        """profile.get_auth v1. Returns (auth_token, auth_secret)."""
        params: dict = {"method": "profile.get_auth"}
        if user_id is not None:
            params["user_id"] = user_id
        payload = self._call(params)
        profile = self._unwrap(payload, "profile")
        if isinstance(profile, dict) and "auth_token" in profile:
            return (profile["auth_token"], profile["auth_secret"])
        return profile

    # ------------------------- Native APIs (REST URL endpoints) -------------------------

    def natural_language_processing_v1(
        self,
        user_input: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """natural.language.processing v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `nlp`. user_input limited to 1000 chars.
        """
        body: dict = {"user_input": user_input}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/natural-language-processing/v1",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._unwrap(payload, "food_response", list_key=None) or []
        return payload

    def image_recognition_v1(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """image.recognition v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `image-recognition`. image_b64 max ~999,982 chars.
        """
        body: dict = {"image_b64": image_b64}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/image-recognition/v1",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._unwrap(payload, "food_response", list_key=None) or []
        return payload

    def image_recognition_v2(
        self,
        image_b64: str,
        include_food_data: Optional[bool] = None,
        eaten_foods: Optional[list] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> list:
        """image.recognition v2. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `image-recognition`. Faster inference, better
        handling of generic/restaurant/mixed foods.
        """
        body: dict = {"image_b64": image_b64}
        if include_food_data is not None:
            body["include_food_data"] = include_food_data
        if eaten_foods is not None:
            body["eaten_foods"] = eaten_foods
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/image-recognition/v2",
            method="POST",
            json_body=body,
        )
        if isinstance(payload, dict) and "food_response" in payload:
            return self._unwrap(payload, "food_response", list_key=None) or []
        return payload

    # ------------------------- Feedback (REST URL endpoint) -------------------------

    def feedback_v1(
        self,
        issue_type_id: int,
        external_id: str,
        barcode: Optional[int] = None,
        issue_type: Optional[str] = None,
        notes: Optional[str] = None,
        returned_food_id: Optional[int] = None,
        returned_serving_id: Optional[int] = None,
        image_file_extension: Optional[str] = None,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ) -> dict:
        """feedback v1. URL-based REST endpoint (POST).

        Premier-exclusive. OAuth2 scope: `feedback`. issue_type_id codes:
        1=Wrong Name/Brand, 2=Wrong Nutrition, 3=Missing Serving Size,
        4=Barcode not found, 99=Other.
        """
        body: dict = {"issue_type_id": issue_type_id, "external_id": external_id}
        if barcode is not None:
            body["barcode"] = barcode
        if issue_type is not None:
            body["issue_type"] = issue_type
        if notes is not None:
            body["notes"] = notes
        if returned_food_id is not None or returned_serving_id is not None:
            returned_food: dict = {}
            if returned_food_id is not None:
                returned_food["food_id"] = returned_food_id
            if returned_serving_id is not None:
                returned_food["serving_id"] = returned_serving_id
            body["returned_food"] = returned_food
        if image_file_extension is not None:
            body["image_file_extension"] = image_file_extension
        if region is not None:
            body["region"] = region
        if language is not None:
            body["language"] = language
        payload = self._call(
            params={"format": "json"},
            url="https://platform.fatsecret.com/rest/feedback/v1",
            method="POST",
            json_body=body,
        )
        return payload
