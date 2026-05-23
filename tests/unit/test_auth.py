import os

import pytest
from dotenv import load_dotenv

from fatsecret import Fatsecret

# Load environment variables
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv()


@pytest.fixture(scope="module")
def valid_credentials():
    """Provide valid credentials from environment."""
    return {
        "username": os.getenv("FATSECRET_USERNAME"),
        "password": os.getenv("FATSECRET_PASSWORD"),
        "consumer_key": os.getenv("FATSECRET_CONSUMER_KEY"),
        "consumer_secret": os.getenv("FATSECRET_CONSUMER_SECRET"),
    }


@pytest.fixture(scope="module")
def invalid_credentials():
    """Provide intentionally invalid credentials for failure testing."""
    return {
        "username": "invalid_user_" + os.urandom(8).hex() + "@example.com",
        "password": "WrongPassword123!" + os.urandom(8).hex(),
        "consumer_key": os.getenv("FATSECRET_CONSUMER_KEY", "invalid_key"),
        "consumer_secret": os.getenv("FATSECRET_CONSUMER_SECRET", "invalid_secret"),
    }


class TestAuthenticationSuccess:
    """Tests for successful authentication scenarios."""

    def test_authenticate_with_valid_credentials(self, valid_credentials):
        """Test successful authentication with valid real credentials."""
        if not all(valid_credentials.values()):
            pytest.skip("Missing required environment variables for authentication")

        result = Fatsecret.fatsecret_authenticate(
            valid_credentials["username"],
            valid_credentials["password"],
            valid_credentials["consumer_key"],
            valid_credentials["consumer_secret"],
        )

        assert (
            result is not None
        ), "Authentication should succeed with valid credentials"
        assert hasattr(result, "authenticate"), "Result should be a Fatsecret instance"
        assert hasattr(result, "get_authorize_url"), "Result should have OAuth methods"

        # Clean up
        if result:
            result.close()


class TestAuthenticationFailures:
    """Aggressive failure testing with real API calls.

    fatsecret_authenticate no longer swallows exceptions and returns
    None on failure — it raises whatever the underlying HTTP/parse
    layer raises (HTTPError, RuntimeError, KeyError, etc.). Tests
    assert that *something* propagates rather than asserting a specific
    type, because FatSecret's response shapes for bad input are not
    contractual.
    """

    def test_invalid_username_real_api(self, valid_credentials):
        """Test with completely invalid username against real API."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                "nonexistent_user_" + os.urandom(16).hex() + "@fakeemail.xyz",
                valid_credentials["password"],
                valid_credentials["consumer_key"],
                valid_credentials["consumer_secret"],
            )

    def test_invalid_password_real_api(self, valid_credentials):
        """Test with wrong password against real API."""
        if not all(valid_credentials.values()):
            pytest.skip("Missing required environment variables")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                valid_credentials["username"],
                "CompletelyWrongPassword123!@#" + os.urandom(8).hex(),
                valid_credentials["consumer_key"],
                valid_credentials["consumer_secret"],
            )

    def test_empty_username(self, valid_credentials):
        """Test with empty username."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                "",
                valid_credentials["password"],
                valid_credentials["consumer_key"],
                valid_credentials["consumer_secret"],
            )

    def test_empty_password(self, valid_credentials):
        """Test with empty password."""
        if not all([valid_credentials["username"], valid_credentials["consumer_key"]]):
            pytest.skip("Missing required credentials")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                valid_credentials["username"],
                "",
                valid_credentials["consumer_key"],
                valid_credentials["consumer_secret"],
            )

    def test_invalid_consumer_key(self, valid_credentials):
        """Test with invalid consumer key."""
        if not valid_credentials["username"]:
            pytest.skip("Missing username")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                valid_credentials["username"],
                valid_credentials["password"],
                "invalid_consumer_key_" + os.urandom(16).hex(),
                valid_credentials["consumer_secret"],
            )

    def test_invalid_consumer_secret(self, valid_credentials):
        """Test with invalid consumer secret."""
        if not valid_credentials["username"]:
            pytest.skip("Missing username")

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                valid_credentials["username"],
                valid_credentials["password"],
                valid_credentials["consumer_key"],
                "invalid_consumer_secret_" + os.urandom(16).hex(),
            )

    def test_special_characters_in_username(self, valid_credentials):
        """Test with special characters that might break URL encoding."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        special_usernames = [
            "user+test@example.com",
            "user%20space@example.com",
            "user&ampersand@example.com",
            "user'quote@example.com",
            'user"doublequote@example.com',
            "user<tag>@example.com",
        ]

        for username in special_usernames:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    username,
                    valid_credentials["password"],
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_special_characters_in_password(self, valid_credentials):
        """Test with special characters that might break form submission."""
        if not all([valid_credentials["username"], valid_credentials["consumer_key"]]):
            pytest.skip("Missing required credentials")

        special_passwords = [
            "P@ssw0rd!#$%",
            "Pass&ampersand",
            "Pass'quote",
            'Pass"double',
            "Pass<tag>",
            "Pass%20space",
            "Pass\nNewline",
            "Pass\tTab",
        ]

        for password in special_passwords:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    valid_credentials["username"],
                    password,
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_very_long_credentials(self, valid_credentials):
        """Test with extremely long credential strings."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        long_username = "a" * 1000 + "@example.com"
        long_password = "P@ssw0rd" + "x" * 1000

        with pytest.raises(Exception):
            Fatsecret.fatsecret_authenticate(
                long_username,
                long_password,
                valid_credentials["consumer_key"],
                valid_credentials["consumer_secret"],
            )

    def test_null_like_values(self, valid_credentials):
        """Test with null-like values."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        # Test None-like string values
        null_values = ["null", "NULL", "None", "undefined", "nil"]

        for null_val in null_values:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    null_val,
                    null_val,
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_sql_injection_attempts(self, valid_credentials):
        """Test with SQL injection patterns (should be safely handled)."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        injection_patterns = [
            "admin' OR '1'='1",
            "admin'--",
            "admin' /*",
            "' OR 1=1--",
            "admin'; DROP TABLE users--",
        ]

        for pattern in injection_patterns:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    pattern,
                    pattern,
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_xss_attempts(self, valid_credentials):
        """Test with XSS patterns (should be safely handled)."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        xss_patterns = [
            "<script>alert('xss')</script>",
            "javascript:alert(1)",
            "<img src=x onerror=alert(1)>",
            "';alert(String.fromCharCode(88,83,83))//",
        ]

        for pattern in xss_patterns:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    pattern,
                    pattern,
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_unicode_credentials(self, valid_credentials):
        """Test with unicode characters in credentials."""
        if not valid_credentials["consumer_key"]:
            pytest.skip("Missing consumer credentials")

        unicode_strings = [
            "用户@example.com",  # Chinese
            "пользователь@example.com",  # Cyrillic
            "مستخدم@example.com",  # Arabic
            "🔥💯🚀@example.com",  # Emoji
            "user\u0000@example.com",  # Null byte
        ]

        for unicode_str in unicode_strings:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    unicode_str,
                    "password",
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )

    def test_whitespace_variations(self, valid_credentials):
        """Test with various whitespace in credentials."""
        if not all([valid_credentials["username"], valid_credentials["consumer_key"]]):
            pytest.skip("Missing required credentials")

        # Should fail because whitespace makes them invalid
        whitespace_tests = [
            " " + valid_credentials["username"],  # Leading space
            valid_credentials["username"] + " ",  # Trailing space
            " " + valid_credentials["username"] + " ",  # Both
            "\t" + valid_credentials["username"],  # Tab
            "\n" + valid_credentials["username"],  # Newline
        ]

        for test_user in whitespace_tests:
            with pytest.raises(Exception):
                Fatsecret.fatsecret_authenticate(
                    test_user,
                    valid_credentials["password"],
                    valid_credentials["consumer_key"],
                    valid_credentials["consumer_secret"],
                )
