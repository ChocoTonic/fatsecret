"""Errors raised by the unofficial FatSecret member-website client."""


class FatsecretWebError(RuntimeError):
    """Base error for the unofficial member-website client."""


class FatsecretWebAuthenticationError(FatsecretWebError):
    """Raised when member-website authentication fails."""


class FatsecretWebParseError(FatsecretWebError):
    """Raised when the member website no longer matches the expected shape."""


class FatsecretWebVerificationError(FatsecretWebError):
    """Raised when a write cannot be verified from subsequently read state."""

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class FatsecretWebNotFoundError(FatsecretWebError):
    """Raised when an owned member resource cannot be found."""


class FatsecretWebRateLimitError(FatsecretWebError):
    """Raised when FatSecret rejects a request because of rate limiting."""

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class FatsecretWebIdempotencyConflictError(FatsecretWebError):
    """Raised when an idempotency key is reused for another request."""


__all__ = [
    "FatsecretWebAuthenticationError",
    "FatsecretWebError",
    "FatsecretWebIdempotencyConflictError",
    "FatsecretWebNotFoundError",
    "FatsecretWebParseError",
    "FatsecretWebRateLimitError",
    "FatsecretWebVerificationError",
]
