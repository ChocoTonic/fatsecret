"""Errors raised by the unofficial FatSecret member-website client."""


class FatsecretWebError(RuntimeError):
    """Base error for the unofficial member-website client."""


class FatsecretWebAuthenticationError(FatsecretWebError):
    """Raised when member-website authentication fails."""


class FatsecretWebParseError(FatsecretWebError):
    """Raised when the member website no longer matches the expected shape."""


class FatsecretWebVerificationError(FatsecretWebError):
    """Raised when a write cannot be verified from subsequently read state."""


__all__ = [
    "FatsecretWebAuthenticationError",
    "FatsecretWebError",
    "FatsecretWebParseError",
    "FatsecretWebVerificationError",
]
