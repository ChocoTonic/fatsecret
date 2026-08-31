"""Optional FastAPI facade for the unofficial member-website client."""

from __future__ import annotations

import json
import os
import secrets
import threading
from pathlib import Path
from typing import Callable

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, Header, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .client import FatsecretWebClient
from .errors import (
    FatsecretWebAuthenticationError,
    FatsecretWebIdempotencyConflictError,
    FatsecretWebNotFoundError,
    FatsecretWebParseError,
    FatsecretWebRateLimitError,
    FatsecretWebVerificationError,
)
from .models import (
    WebIngredientWrite,
    WebRecipeCopyRequest,
    WebRecipeWrite,
)
from .service import IdempotencyStore, RecipeCopyService, RecipeOperationStore


class RdiReplace(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calories_per_day: int = Field(gt=0, le=100_000)


class MemberWebFacadeSettings(BaseModel):
    """Validated runtime configuration for the single-account facade."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bearer_token: SecretStr = Field(min_length=1)
    database_path: Path = Path("fatsecret-member-facade.sqlite3")
    username: str | None = None
    password: SecretStr | None = None
    client_timeout: float = Field(default=30, gt=0)
    client_retries: bool = True
    wait_on_rate_limit: bool = True
    default_retry_after: int = Field(default=300, gt=0)
    mutation_delay_seconds: float = Field(default=1.0, ge=0)
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(default=8000, ge=1, le=65_535)

    @classmethod
    def from_env(
        cls,
        *,
        bearer_token: str | None = None,
        database_path: str | Path | None = None,
    ) -> "MemberWebFacadeSettings":
        """Load settings from the documented ``FATSECRET_*`` variables."""

        token = bearer_token or os.environ.get("FATSECRET_FACADE_TOKEN")
        if not token:
            raise ValueError("FATSECRET_FACADE_TOKEN must be configured")
        return cls(
            bearer_token=token,
            database_path=database_path
            or os.environ.get("FATSECRET_FACADE_DB", "fatsecret-member-facade.sqlite3"),
            username=os.environ.get("FATSECRET_USERNAME"),
            password=os.environ.get("FATSECRET_PASSWORD"),
            client_timeout=os.environ.get("FATSECRET_WEB_TIMEOUT", "30"),
            client_retries=_environment_bool("FATSECRET_WEB_RETRIES", True),
            wait_on_rate_limit=_environment_bool(
                "FATSECRET_WEB_WAIT_ON_RATE_LIMIT", True
            ),
            default_retry_after=os.environ.get(
                "FATSECRET_FACADE_DEFAULT_RETRY_AFTER", "300"
            ),
            mutation_delay_seconds=os.environ.get(
                "FATSECRET_FACADE_MUTATION_DELAY_SECONDS", "1"
            ),
            host=os.environ.get("FATSECRET_FACADE_HOST", "127.0.0.1"),
            port=os.environ.get("FATSECRET_FACADE_PORT", "8000"),
        )


def _environment_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    normalized = raw.strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


class ProblemException(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        title: str,
        *,
        detail: str | None = None,
        retryable: bool = False,
        upstream_outcome: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self.retryable = retryable
        self.upstream_outcome = upstream_outcome
        self.headers = headers or {}


def _problem_response(request: Request, error: ProblemException) -> JSONResponse:
    body = {
        "type": f"https://fatsecret.readthedocs.io/problems/{error.code}",
        "title": error.title,
        "status": error.status,
        "detail": error.detail,
        "instance": str(request.url.path),
        "code": error.code,
        "retryable": error.retryable,
    }
    if error.upstream_outcome is not None:
        body["upstream_outcome"] = error.upstream_outcome
    return JSONResponse(
        status_code=error.status,
        content=body,
        media_type="application/problem+json",
        headers=error.headers,
    )


def _stored_response(row: dict) -> JSONResponse:
    state = row["state"]
    if state == "completed":
        headers = {"Idempotent-Replayed": "true"}
        if row["location"]:
            headers["Location"] = row["location"]
        return JSONResponse(
            status_code=row["status_code"],
            content=json.loads(row["response_json"]),
            headers=headers,
        )
    if state == "unknown":
        raise ProblemException(
            504,
            "upstream_write_ambiguous",
            "Previous write outcome is unknown",
            detail=row["error"],
            upstream_outcome="unknown",
        )
    raise ProblemException(
        409,
        "idempotency_request_in_progress",
        "A request with this idempotency key is still in progress",
        retryable=True,
    )


def create_app(
    *,
    client_factory: Callable[[], FatsecretWebClient] | None = None,
    bearer_token: str | None = None,
    database_path: str | Path | None = None,
    settings: MemberWebFacadeSettings | None = None,
) -> FastAPI:
    """Create a single-account member-web facade application."""

    if settings is not None and (bearer_token is not None or database_path is not None):
        raise ValueError(
            "settings cannot be combined with bearer_token or database_path"
        )
    config = settings or MemberWebFacadeSettings.from_env(
        bearer_token=bearer_token, database_path=database_path
    )
    if client_factory is None:
        if not config.username or not config.password:
            raise ValueError("FATSECRET_USERNAME and FATSECRET_PASSWORD are required")

        def client_factory() -> FatsecretWebClient:
            return FatsecretWebClient(
                config.username,
                config.password.get_secret_value(),
                timeout=config.client_timeout,
                retries=config.client_retries,
                wait_on_rate_limit=config.wait_on_rate_limit,
                default_retry_after=config.default_retry_after,
            )

    operation_store = RecipeOperationStore(config.database_path)
    idempotency_store = IdempotencyStore(config.database_path)
    mutation_lock = threading.Lock()
    copy_service = RecipeCopyService(
        client_factory,
        operation_store,
        default_retry_after=config.default_retry_after,
        mutation_lock=mutation_lock,
        mutation_delay_seconds=config.mutation_delay_seconds,
    )
    bearer = HTTPBearer(auto_error=False)
    app = FastAPI(
        title="FatSecret Member-Web Facade API",
        version="0.2.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if (
            credentials is None
            or credentials.scheme.casefold() != "bearer"
            or not secrets.compare_digest(
                credentials.credentials, config.bearer_token.get_secret_value()
            )
        ):
            raise ProblemException(
                401,
                "invalid_bearer_token",
                "Valid bearer authentication is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

    secured = [Depends(authenticate)]

    @app.exception_handler(ProblemException)
    def handle_problem(request: Request, error: ProblemException) -> JSONResponse:
        return _problem_response(request, error)

    @app.exception_handler(RequestValidationError)
    def handle_validation(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                422,
                "validation_failed",
                "Request validation failed",
                detail=str(error),
            ),
        )

    @app.exception_handler(FatsecretWebNotFoundError)
    def handle_not_found(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                404,
                "member_resource_not_found",
                "Resource not found",
                detail=str(error),
            ),
        )

    @app.exception_handler(FatsecretWebIdempotencyConflictError)
    def handle_idempotency_conflict(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                409,
                "idempotency_conflict",
                "Idempotency key conflict",
                detail=str(error),
            ),
        )

    @app.exception_handler(FatsecretWebRateLimitError)
    def handle_rate_limit(
        request: Request, error: FatsecretWebRateLimitError
    ) -> JSONResponse:
        delay = error.retry_after or 300
        return _problem_response(
            request,
            ProblemException(
                429,
                "upstream_rate_limited",
                "FatSecret rate limit exceeded",
                detail=str(error),
                retryable=True,
                headers={"Retry-After": str(delay)},
            ),
        )

    @app.exception_handler(FatsecretWebVerificationError)
    def handle_verification(
        request: Request, error: FatsecretWebVerificationError
    ) -> JSONResponse:
        headers = (
            {"Retry-After": str(error.retry_after)}
            if error.retry_after is not None
            else None
        )
        return _problem_response(
            request,
            ProblemException(
                504,
                "upstream_write_ambiguous",
                "Upstream write could not be verified",
                detail=str(error),
                upstream_outcome="unknown",
                headers=headers,
            ),
        )

    @app.exception_handler(FatsecretWebParseError)
    def handle_parse(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                502,
                "upstream_contract_changed",
                "FatSecret response could not be parsed",
                detail=str(error),
            ),
        )

    @app.exception_handler(FatsecretWebAuthenticationError)
    def handle_upstream_auth(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                502,
                "upstream_authentication_failed",
                "FatSecret authentication failed",
                detail=str(error),
            ),
        )

    @app.exception_handler(requests.RequestException)
    def handle_upstream_http(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                502,
                "upstream_http_failure",
                "FatSecret request failed",
                detail=str(error),
                retryable=True,
            ),
        )

    @app.exception_handler(ValueError)
    def handle_value_error(request: Request, error: Exception) -> JSONResponse:
        return _problem_response(
            request,
            ProblemException(
                422,
                "invalid_member_request",
                "Member operation request is invalid",
                detail=str(error),
            ),
        )

    @app.get("/v1/member/rdi", dependencies=secured)
    def get_rdi():
        with client_factory() as client:
            return client.get_rdi()

    @app.put("/v1/member/rdi", dependencies=secured)
    def replace_rdi(body: RdiReplace):
        with mutation_lock, client_factory() as client:
            return client.set_rdi(body.calories_per_day)

    @app.get("/v1/member/recipes", dependencies=secured)
    def list_recipes():
        with client_factory() as client:
            items = client.list_recipes()
        return {"items": items, "count": len(items)}

    @app.post("/v1/member/recipes", dependencies=secured, status_code=201)
    def create_recipe(
        body: WebRecipeWrite,
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        scope = "POST /v1/member/recipes"
        existing = idempotency_store.begin(
            scope, idempotency_key, body.model_dump(mode="json")
        )
        if existing is not None:
            return _stored_response(existing)
        try:
            with mutation_lock, client_factory() as client:
                result = client.create_recipe(body)
        except Exception as error:
            idempotency_store.mark_unknown(scope, idempotency_key, error)
            raise
        location = f"/v1/member/recipes/{result.recipe_id}"
        idempotency_store.complete(
            scope,
            idempotency_key,
            status_code=201,
            response=result,
            location=location,
        )
        return JSONResponse(
            status_code=201,
            content=result.model_dump(mode="json"),
            headers={"Location": location},
        )

    @app.get("/v1/member/recipes/{recipe_id}", dependencies=secured)
    def get_recipe(recipe_id: int):
        with client_factory() as client:
            return client.get_recipe(recipe_id)

    @app.put("/v1/member/recipes/{recipe_id}", dependencies=secured)
    def replace_recipe(recipe_id: int, body: WebRecipeWrite):
        with mutation_lock, client_factory() as client:
            return client.replace_recipe(recipe_id, body)

    @app.delete("/v1/member/recipes/{recipe_id}", dependencies=secured, status_code=204)
    def delete_recipe(recipe_id: int) -> Response:
        with mutation_lock, client_factory() as client:
            client.delete_recipe(recipe_id)
        return Response(status_code=204)

    @app.get(
        "/v1/member/recipes/{recipe_id}/foods/{food_id}/portions",
        dependencies=secured,
    )
    def list_food_portions(recipe_id: int, food_id: int):
        with client_factory() as client:
            return client.list_food_portions(recipe_id, food_id)

    @app.post(
        "/v1/member/recipes/{recipe_id}/ingredients",
        dependencies=secured,
        status_code=201,
    )
    def add_ingredient(
        recipe_id: int,
        body: WebIngredientWrite,
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        scope = f"POST /v1/member/recipes/{recipe_id}/ingredients"
        existing = idempotency_store.begin(
            scope, idempotency_key, body.model_dump(mode="json")
        )
        if existing is not None:
            return _stored_response(existing)
        try:
            with mutation_lock, client_factory() as client:
                result = client.add_recipe_ingredient(recipe_id, body)
        except Exception as error:
            idempotency_store.mark_unknown(scope, idempotency_key, error)
            raise
        location = f"/v1/member/recipes/{recipe_id}/ingredients/{result.entry_id}"
        idempotency_store.complete(
            scope,
            idempotency_key,
            status_code=201,
            response=result,
            location=location,
        )
        return JSONResponse(
            status_code=201,
            content=result.model_dump(mode="json"),
            headers={"Location": location},
        )

    @app.put(
        "/v1/member/recipes/{recipe_id}/ingredients/{entry_id}",
        dependencies=secured,
    )
    def replace_ingredient(recipe_id: int, entry_id: int, body: WebIngredientWrite):
        with mutation_lock, client_factory() as client:
            return client.replace_recipe_ingredient(recipe_id, entry_id, body)

    @app.delete(
        "/v1/member/recipes/{recipe_id}/ingredients/{entry_id}",
        dependencies=secured,
        status_code=204,
    )
    def delete_ingredient(recipe_id: int, entry_id: int) -> Response:
        with mutation_lock, client_factory() as client:
            client.delete_recipe_ingredient(recipe_id, entry_id)
        return Response(status_code=204)

    @app.post(
        "/v1/member/recipes/{recipe_id}/copies",
        dependencies=secured,
        status_code=202,
    )
    def copy_recipe(
        recipe_id: int,
        body: WebRecipeCopyRequest,
        background_tasks: BackgroundTasks,
        idempotency_key: str = Header(alias="Idempotency-Key"),
    ):
        operation = copy_service.start_copy(recipe_id, body.title, idempotency_key)
        if operation.status not in {"completed", "running"}:
            background_tasks.add_task(copy_service.run_copy, operation.operation_id)
        location = f"/v1/member/operations/{operation.operation_id}"
        return JSONResponse(
            status_code=202,
            content=operation.model_dump(mode="json"),
            headers={"Location": location},
        )

    @app.get("/v1/member/operations/{operation_id}", dependencies=secured)
    def get_operation(operation_id: str):
        operation = copy_service.get_copy(operation_id)
        if operation is None:
            raise FatsecretWebNotFoundError(
                f"copy operation {operation_id} was not found"
            )
        return operation

    @app.post(
        "/v1/member/operations/{operation_id}/resume",
        dependencies=secured,
        status_code=202,
    )
    def resume_operation(operation_id: str, background_tasks: BackgroundTasks):
        operation = copy_service.get_copy(operation_id)
        if operation is None:
            raise FatsecretWebNotFoundError(
                f"copy operation {operation_id} was not found"
            )
        background_tasks.add_task(copy_service.run_copy, operation_id)
        return operation

    return app


def main() -> None:
    """Run the facade from environment configuration."""

    try:
        import uvicorn
    except ImportError as error:  # pragma: no cover - packaging guidance
        raise RuntimeError(
            "install fatsecret[facade] to run the HTTP facade"
        ) from error
    settings = MemberWebFacadeSettings.from_env()
    uvicorn.run(create_app(settings=settings), host=settings.host, port=settings.port)


__all__ = ["MemberWebFacadeSettings", "create_app", "main"]
