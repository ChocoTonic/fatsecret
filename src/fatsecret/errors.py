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
