class BaseFatsecretError(Exception):
    """Base exception for Fatsecret API errors.

    Carries the original numeric `code` and textual `message` returned by the API
    for easier programmatic access in callers/tests.
    """

    def __init__(self, code, message):
        super().__init__(f"Error {code}: {message}")
        self.code = code
        self.message = message


class GeneralError(BaseFatsecretError):
    def __init__(self, code, message):
        super().__init__(code, message)


class AuthenticationError(BaseFatsecretError):
    def __init__(self, code, message):
        super().__init__(code, message)


class ParameterError(BaseFatsecretError):
    def __init__(self, code, message):
        super().__init__(code, message)


class ApplicationError(BaseFatsecretError):
    def __init__(self, code, message):
        super().__init__(code, message)


class ScopeRequiredError(ApplicationError):
    """Raised when the upstream rejects a call because the access token lacks a required scope."""


class PremierRequiredError(ScopeRequiredError):
    """Raised when an endpoint requires the `premier` scope and the token doesn't carry it."""
