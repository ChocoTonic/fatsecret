from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MethodRef:
    """A (method, version) pair identified during discovery."""

    method: str  # e.g. "foods.search"
    version: str  # e.g. "v1"

    @property
    def url(self) -> str:
        from .config import DOCS_ROOT

        return f"{DOCS_ROOT}/{self.version}/{self.method}"

    @property
    def slug(self) -> str:
        return f"{self.method.replace('.', '_')}_{self.version}"


@dataclass
class Parameter:
    name: str
    type: str | None = None
    required: bool = False
    description: str = ""
    default: str | None = None


@dataclass
class EndpointSpec:
    ref: MethodRef
    exists: bool = True
    deprecated: bool = False
    http_verb: str = "GET"
    api_method_param: str | None = None  # e.g. "foods.search.v2"
    rest_url: str | None = None  # for native APIs that use REST paths
    oauth: list[str] = field(default_factory=lambda: ["oauth1"])
    scope: str = "basic"
    premier: bool = False
    parameters: list[Parameter] = field(default_factory=list)
    response: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    parse_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_url": self.ref.url,
            "method": self.ref.method,
            "version": self.ref.version,
            "exists": self.exists,
            "deprecated": self.deprecated,
            "http_verb": self.http_verb,
            "api_method_param": self.api_method_param,
            "rest_url": self.rest_url,
            "oauth": list(self.oauth),
            "scope": self.scope,
            "premier": self.premier,
            "parameters": [p.__dict__ for p in self.parameters],
            "response": self.response,
            "notes": self.notes,
            "parse_warnings": list(self.parse_warnings),
        }
