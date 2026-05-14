"""Base class for v2.0 resource-namespaced wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..fatsecret import Fatsecret


class BaseResource:
    """Common scaffold for every resource.

    Resources hold a back-reference to the `Fatsecret` client so they can
    delegate to its existing flat methods during Phase 1, and to its
    `_call`/`_check_errors`/`_unwrap` helpers once Phase 5 codegen replaces
    delegation with real implementations.
    """

    __slots__ = ("_client",)

    def __init__(self, client: "Fatsecret") -> None:
        self._client = client
