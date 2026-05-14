"""Exhaustive unit tests for the Native APIs + Feedback resources.

Covers four method-version pairs, all Premier-exclusive REST-URL POST endpoints:

  * natural.language.processing  v1  -> ``natural_language_processing_v1``
  * image.recognition            v1  -> ``image_recognition_v1``
  * image.recognition            v2  -> ``image_recognition_v2``
  * feedback                     v1  -> ``feedback_v1``

These differ from the rest of the SDK in three important ways, all of which
this file exercises:

  1. They use a REST URL path (passed as ``url=``) instead of the legacy
     ``?method=`` query parameter.  Tests assert that NO ``method=`` key
     appears in the ``params`` dict sent to ``_call``.
  2. They are HTTP POST.  Tests assert ``method="POST"`` (the HTTP-verb
     keyword on ``_call``).
  3. The payload is sent as a JSON body via ``json_body=``, not as form/query
     params.  Tests assert ``json_body`` contains required parameters and
     optionals only when supplied.

Per method-version we assert:
  * Happy path: correct URL, HTTP verb, ``json_body`` shape, ``params`` is
    just ``{"format": "json"}`` with no API ``method`` key.
  * Every optional parameter, both individually and en masse:
    present-when-set, absent-when-``None``.
  * Return-shape: ``food_response`` is unwrapped to a list (NLP /
    image-recognition); feedback returns the raw payload dict containing
    the three signed PUT URLs + ``contentTypeHeader``.
  * ``PremierRequiredError`` propagation (all four methods are Premier).
  * ``ScopeRequiredError`` propagation (per-method OAuth2 scope check).

image_recognition specifics:
  * ``image_b64`` is passed through verbatim - the wrapper does NOT
    re-encode.  The 999,982-char upper bound is upstream's problem.
  * v2 accepts WebP (per the YAML).  The wrapper takes no format hint, so
    we just verify the same call shape works for a WebP-like payload.
"""

from unittest.mock import MagicMock, patch

import pytest

from fatsecret import Fatsecret, PremierRequiredError, ScopeRequiredError


# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

NLP_URL = "https://platform.fatsecret.com/rest/natural-language-processing/v1"
IMG_V1_URL = "https://platform.fatsecret.com/rest/image-recognition/v1"
IMG_V2_URL = "https://platform.fatsecret.com/rest/image-recognition/v2"
FEEDBACK_URL = "https://platform.fatsecret.com/rest/feedback/v1"


@pytest.fixture
def fs():
    with patch("fatsecret.fatsecret.OAuth1Service") as mock_oauth1:
        mock_oauth1.return_value.get_session.return_value = MagicMock()
        return Fatsecret("ck", "cs")


def _assert_url_post_call(mock_call, expected_url):
    """Common assertion: REST URL POST endpoint with no ``method=`` API param."""
    kwargs = mock_call.call_args.kwargs
    assert kwargs["url"] == expected_url
    assert kwargs["method"] == "POST"
    # params is the query-string dict; for URL endpoints it carries only format.
    assert kwargs["params"] == {"format": "json"}
    assert "method" not in kwargs["params"]
    return kwargs


# ===========================================================================
# natural.language.processing v1
# ===========================================================================


def test_nlp_v1_happy_path_minimal(fs):
    payload = {"food_response": [{"food_id": "1", "food_entry_name": "apple"}]}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = fs.natural_language_processing_v1("I ate an apple")

    kwargs = _assert_url_post_call(mock_call, NLP_URL)
    body = kwargs["json_body"]
    assert body == {"user_input": "I ate an apple"}
    # No optionals leaked.
    for opt in ("include_food_data", "eaten_foods", "region", "language"):
        assert opt not in body
    assert result == [{"food_id": "1", "food_entry_name": "apple"}]


def test_nlp_v1_all_optionals_present_when_supplied(fs):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.natural_language_processing_v1(
            "two eggs and toast",
            include_food_data=True,
            eaten_foods=[{"food_id": "42"}],
            region="US",
            language="en",
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["user_input"] == "two eggs and toast"
    assert body["include_food_data"] is True
    assert body["eaten_foods"] == [{"food_id": "42"}]
    assert body["region"] == "US"
    assert body["language"] == "en"


@pytest.mark.parametrize(
    "kwarg,value",
    [
        ("include_food_data", True),
        ("include_food_data", False),
        ("eaten_foods", [{"food_id": "1"}]),
        ("region", "GB"),
        ("language", "fr"),
    ],
)
def test_nlp_v1_each_optional_individually(fs, kwarg, value):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.natural_language_processing_v1("hello", **{kwarg: value})
    body = mock_call.call_args.kwargs["json_body"]
    assert body[kwarg] == value
    others = {"include_food_data", "eaten_foods", "region", "language"} - {kwarg}
    for o in others:
        assert o not in body


def test_nlp_v1_omits_optionals_when_none(fs):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        fs.natural_language_processing_v1(
            "x",
            include_food_data=None,
            eaten_foods=None,
            region=None,
            language=None,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body == {"user_input": "x"}


def test_nlp_v1_response_with_list_passthrough(fs):
    payload = {
        "food_response": [
            {"food_id": "1", "food_entry_name": "apple"},
            {"food_id": "2", "food_entry_name": "egg"},
        ]
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = fs.natural_language_processing_v1("apple and egg")
    assert result == [
        {"food_id": "1", "food_entry_name": "apple"},
        {"food_id": "2", "food_entry_name": "egg"},
    ]


def test_nlp_v1_response_with_empty_list_returns_empty(fs):
    with patch.object(
        Fatsecret, "_call", return_value={"food_response": []}
    ):
        result = fs.natural_language_processing_v1("nothing")
    assert result == []


def test_nlp_v1_response_without_food_response_passes_through(fs):
    # The wrapper only unwraps when the key is present; otherwise it returns
    # the raw payload (defensive against future schema changes).
    raw = {"something_else": "value"}
    with patch.object(Fatsecret, "_call", return_value=raw):
        result = fs.natural_language_processing_v1("x")
    assert result == raw


def test_nlp_v1_propagates_premier_required(fs):
    with patch.object(
        Fatsecret, "_call",
        side_effect=PremierRequiredError(207, "Premier required"),
    ):
        with pytest.raises(PremierRequiredError):
            fs.natural_language_processing_v1("x")


def test_nlp_v1_propagates_scope_required(fs):
    with patch.object(
        Fatsecret, "_call",
        side_effect=ScopeRequiredError(208, "nlp scope required"),
    ):
        with pytest.raises(ScopeRequiredError):
            fs.natural_language_processing_v1("x")


# ===========================================================================
# image.recognition v1 + v2 (parameterised - same signature, different URL)
# ===========================================================================

IMG_VERSIONS = [
    ("image_recognition_v1", IMG_V1_URL),
    ("image_recognition_v2", IMG_V2_URL),
]


@pytest.mark.parametrize("method_name,expected_url", IMG_VERSIONS)
def test_image_recognition_happy_path_minimal(fs, method_name, expected_url):
    payload = {"food_response": [{"food_id": "9", "food_entry_name": "pizza"}]}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        result = getattr(fs, method_name)("BASE64IMG")

    kwargs = _assert_url_post_call(mock_call, expected_url)
    body = kwargs["json_body"]
    assert body == {"image_b64": "BASE64IMG"}
    for opt in ("include_food_data", "eaten_foods", "region", "language"):
        assert opt not in body
    assert result == [{"food_id": "9", "food_entry_name": "pizza"}]


@pytest.mark.parametrize("method_name,expected_url", IMG_VERSIONS)
def test_image_recognition_image_b64_is_passed_through_verbatim(
    fs, method_name, expected_url
):
    # The wrapper must NOT re-encode an already-base64 string.  A real-world
    # caller may pass a Standard or URL-safe Base64 string with/without
    # padding; both go straight to the wire.
    samples = [
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        "QUJDREVGRw==",  # "ABCDEFG"
        "A" * 1024,  # not really base64 but the wrapper must not validate
    ]
    for raw in samples:
        with patch.object(Fatsecret, "_call", return_value={"food_response": []}) as mc:
            getattr(fs, method_name)(raw)
        assert mc.call_args.kwargs["json_body"]["image_b64"] == raw


def test_image_recognition_v2_accepts_webp_style_payload(fs):
    # v2 advertises WebP support; the wrapper itself takes no format hint, so
    # we just confirm a typical WebP-base64 prefix flows through unaltered.
    webp_b64 = "UklGRiQAAABXRUJQVlA4IBgAAAAwAQCdASoBAAEAAQAcJaQAA3AA/v3AgAA="
    with patch.object(
        Fatsecret, "_call", return_value={"food_response": []}
    ) as mc:
        fs.image_recognition_v2(webp_b64)
    assert mc.call_args.kwargs["json_body"]["image_b64"] == webp_b64


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_all_optionals_present_when_supplied(
    fs, method_name, _url
):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        getattr(fs, method_name)(
            "IMGB64",
            include_food_data=True,
            eaten_foods=[{"food_id": "1"}, {"food_id": "2"}],
            region="US",
            language="en",
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["image_b64"] == "IMGB64"
    assert body["include_food_data"] is True
    assert body["eaten_foods"] == [{"food_id": "1"}, {"food_id": "2"}]
    assert body["region"] == "US"
    assert body["language"] == "en"


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
@pytest.mark.parametrize(
    "kwarg,value",
    [
        ("include_food_data", True),
        ("include_food_data", False),
        ("eaten_foods", [{"food_id": "1"}]),
        ("region", "AU"),
        ("language", "de"),
    ],
)
def test_image_recognition_each_optional_individually(
    fs, method_name, _url, kwarg, value
):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        getattr(fs, method_name)("IMG", **{kwarg: value})
    body = mock_call.call_args.kwargs["json_body"]
    assert body[kwarg] == value
    others = {"include_food_data", "eaten_foods", "region", "language"} - {kwarg}
    for o in others:
        assert o not in body


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_omits_optionals_when_none(fs, method_name, _url):
    payload = {"food_response": []}
    with patch.object(Fatsecret, "_call", return_value=payload) as mock_call:
        getattr(fs, method_name)(
            "IMG",
            include_food_data=None,
            eaten_foods=None,
            region=None,
            language=None,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body == {"image_b64": "IMG"}


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_response_list_passthrough(fs, method_name, _url):
    payload = {
        "food_response": [
            {"food_id": "a"},
            {"food_id": "b"},
        ]
    }
    with patch.object(Fatsecret, "_call", return_value=payload):
        result = getattr(fs, method_name)("IMG")
    assert result == [{"food_id": "a"}, {"food_id": "b"}]


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_empty_food_response_returns_empty(
    fs, method_name, _url
):
    with patch.object(
        Fatsecret, "_call", return_value={"food_response": []}
    ):
        result = getattr(fs, method_name)("IMG")
    assert result == []


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_response_without_food_response_passes_through(
    fs, method_name, _url
):
    raw = {"unknown_top_level": [1, 2, 3]}
    with patch.object(Fatsecret, "_call", return_value=raw):
        result = getattr(fs, method_name)("IMG")
    assert result == raw


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_propagates_premier_required(fs, method_name, _url):
    with patch.object(
        Fatsecret, "_call",
        side_effect=PremierRequiredError(207, "Premier required"),
    ):
        with pytest.raises(PremierRequiredError):
            getattr(fs, method_name)("IMG")


@pytest.mark.parametrize("method_name,_url", IMG_VERSIONS)
def test_image_recognition_propagates_scope_required(fs, method_name, _url):
    with patch.object(
        Fatsecret, "_call",
        side_effect=ScopeRequiredError(208, "image-recognition scope required"),
    ):
        with pytest.raises(ScopeRequiredError):
            getattr(fs, method_name)("IMG")


# ===========================================================================
# feedback v1
# ===========================================================================


# Realistic-looking signed PUT response per the YAML.  The wrapper returns
# this dict verbatim; the caller is responsible for PUTting bytes to each URL.
FEEDBACK_PUT_RESPONSE = {
    "barcode": "https://signed.example/barcode?sig=AAA",
    "packaging": "https://signed.example/packaging?sig=BBB",
    "nutrition": "https://signed.example/nutrition?sig=CCC",
    "contentTypeHeader": "image/jpeg",
}


def test_feedback_v1_happy_path_minimal(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        result = fs.feedback_v1(issue_type_id=1, external_id="ext-42")

    kwargs = _assert_url_post_call(mock_call, FEEDBACK_URL)
    body = kwargs["json_body"]
    assert body == {"issue_type_id": 1, "external_id": "ext-42"}
    # None of the optionals leaked.
    for opt in (
        "barcode",
        "issue_type",
        "notes",
        "returned_food",
        "image_file_extension",
        "region",
        "language",
    ):
        assert opt not in body

    # Wrapper returns the raw payload (three signed PUT URLs + header).
    assert result == FEEDBACK_PUT_RESPONSE
    assert result["barcode"].startswith("https://")
    assert result["packaging"].startswith("https://")
    assert result["nutrition"].startswith("https://")
    assert result["contentTypeHeader"] == "image/jpeg"


def test_feedback_v1_all_simple_optionals_present(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(
            issue_type_id=2,
            external_id="ext-1",
            barcode=12345678,
            issue_type="Wrong Nutrition",
            notes="protein looks off",
            image_file_extension="jpg",
            region="US",
            language="en",
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["issue_type_id"] == 2
    assert body["external_id"] == "ext-1"
    assert body["barcode"] == 12345678
    assert body["issue_type"] == "Wrong Nutrition"
    assert body["notes"] == "protein looks off"
    assert body["image_file_extension"] == "jpg"
    assert body["region"] == "US"
    assert body["language"] == "en"
    # ``returned_food`` is built only when food/serving ids are passed.
    assert "returned_food" not in body


@pytest.mark.parametrize(
    "kwarg,value",
    [
        ("barcode", 99999999),
        ("issue_type", "Other"),
        ("notes", "n/a"),
        ("image_file_extension", "png"),
        ("region", "GB"),
        ("language", "fr"),
    ],
)
def test_feedback_v1_each_simple_optional_individually(fs, kwarg, value):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(issue_type_id=99, external_id="e", **{kwarg: value})
    body = mock_call.call_args.kwargs["json_body"]
    assert body[kwarg] == value
    others = {
        "barcode",
        "issue_type",
        "notes",
        "image_file_extension",
        "region",
        "language",
    } - {kwarg}
    for o in others:
        assert o not in body
    assert "returned_food" not in body


def test_feedback_v1_omits_simple_optionals_when_none(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(
            issue_type_id=1,
            external_id="e",
            barcode=None,
            issue_type=None,
            notes=None,
            returned_food_id=None,
            returned_serving_id=None,
            image_file_extension=None,
            region=None,
            language=None,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body == {"issue_type_id": 1, "external_id": "e"}


def test_feedback_v1_returned_food_built_from_food_id_only(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(
            issue_type_id=2,
            external_id="e",
            returned_food_id=555,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["returned_food"] == {"food_id": 555}


def test_feedback_v1_returned_food_built_from_serving_id_only(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(
            issue_type_id=2,
            external_id="e",
            returned_serving_id=777,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["returned_food"] == {"serving_id": 777}


def test_feedback_v1_returned_food_built_from_both_ids(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(
            issue_type_id=2,
            external_id="e",
            returned_food_id=555,
            returned_serving_id=777,
        )
    body = mock_call.call_args.kwargs["json_body"]
    assert body["returned_food"] == {"food_id": 555, "serving_id": 777}


def test_feedback_v1_returned_food_absent_when_both_none(fs):
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(issue_type_id=1, external_id="e")
    assert "returned_food" not in mock_call.call_args.kwargs["json_body"]


@pytest.mark.parametrize("issue_type_id", [1, 2, 3, 4, 99])
def test_feedback_v1_accepts_documented_issue_type_ids(fs, issue_type_id):
    # Per the docstring: 1=Wrong Name/Brand, 2=Wrong Nutrition,
    # 3=Missing Serving Size, 4=Barcode not found, 99=Other.  The wrapper
    # passes the int through without validation.
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ) as mock_call:
        fs.feedback_v1(issue_type_id=issue_type_id, external_id="e")
    assert mock_call.call_args.kwargs["json_body"]["issue_type_id"] == issue_type_id


def test_feedback_v1_returns_raw_payload_shape(fs):
    # The wrapper does NOT unwrap feedback responses - it returns the raw
    # dict containing the three signed PUT URLs + contentTypeHeader.
    with patch.object(
        Fatsecret, "_call", return_value=FEEDBACK_PUT_RESPONSE
    ):
        result = fs.feedback_v1(issue_type_id=1, external_id="e")
    assert set(result.keys()) == {
        "barcode",
        "packaging",
        "nutrition",
        "contentTypeHeader",
    }


def test_feedback_v1_propagates_premier_required(fs):
    with patch.object(
        Fatsecret, "_call",
        side_effect=PremierRequiredError(207, "Premier required"),
    ):
        with pytest.raises(PremierRequiredError):
            fs.feedback_v1(issue_type_id=1, external_id="e")


def test_feedback_v1_propagates_scope_required(fs):
    with patch.object(
        Fatsecret, "_call",
        side_effect=ScopeRequiredError(208, "feedback scope required"),
    ):
        with pytest.raises(ScopeRequiredError):
            fs.feedback_v1(issue_type_id=1, external_id="e")
