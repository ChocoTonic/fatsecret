"""Durable orchestration for multi-request member-website operations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import uuid
from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .client import FatsecretWebClient
from .errors import (
    FatsecretWebIdempotencyConflictError,
    FatsecretWebRateLimitError,
    FatsecretWebVerificationError,
)
from .models import WebRecipeCopyOperation, WebRecipeDetail
from .recipe_parser import metadata_matches


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ingredient_signature(ingredient: object) -> tuple[int, Decimal, int]:
    return (
        int(getattr(ingredient, "food_id")),
        Decimal(getattr(ingredient, "amount")),
        int(getattr(ingredient, "portion_id")),
    )


class RecipeOperationStore:
    """SQLite persistence for recipe-copy progress and idempotency keys."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS recipe_copy_operations (
                    operation_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    request_hash TEXT NOT NULL,
                    source_recipe_id INTEGER NOT NULL,
                    target_title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_recipe_id INTEGER,
                    source_snapshot TEXT,
                    completed_entry_ids TEXT NOT NULL DEFAULT '[]',
                    pre_create_recipe_ids TEXT,
                    result_json TEXT,
                    error TEXT,
                    retry_after TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def create_or_get(
        self,
        *,
        source_recipe_id: int,
        target_title: str,
        idempotency_key: str,
    ) -> WebRecipeCopyOperation:
        if not 8 <= len(idempotency_key) <= 255:
            raise ValueError(
                "idempotency_key must contain between 8 and 255 characters"
            )
        request_hash = hashlib.sha256(
            json.dumps(
                {"source_recipe_id": source_recipe_id, "target_title": target_title},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        now = _utcnow().isoformat()
        with self._lock, closing(self._connect()) as connection:
            existing = connection.execute(
                "SELECT * FROM recipe_copy_operations WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise FatsecretWebIdempotencyConflictError(
                        "idempotency key was already used for a different copy request"
                    )
                return self._to_model(existing)

            operation_id = uuid.uuid4().hex
            connection.execute(
                """
                INSERT INTO recipe_copy_operations (
                    operation_id, idempotency_key, request_hash,
                    source_recipe_id, target_title, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    operation_id,
                    idempotency_key,
                    request_hash,
                    source_recipe_id,
                    target_title,
                    now,
                    now,
                ),
            )
            connection.commit()
            row = connection.execute(
                "SELECT * FROM recipe_copy_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            return self._to_model(row)

    def get(self, operation_id: str) -> WebRecipeCopyOperation | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM recipe_copy_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            return self._to_model(row) if row is not None else None

    def raw(self, operation_id: str) -> dict | None:
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM recipe_copy_operations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def update(self, operation_id: str, **values: object) -> None:
        if not values:
            return
        encoded = {}
        for name, value in values.items():
            if (
                name
                in {
                    "source_snapshot",
                    "completed_entry_ids",
                    "pre_create_recipe_ids",
                    "result_json",
                }
                and value is not None
            ):
                if hasattr(value, "model_dump"):
                    value = value.model_dump(mode="json")
                encoded[name] = json.dumps(value, sort_keys=True)
            elif isinstance(value, datetime):
                encoded[name] = value.isoformat()
            else:
                encoded[name] = value
        encoded["updated_at"] = _utcnow().isoformat()
        assignments = ", ".join(f"{name} = ?" for name in encoded)
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                f"UPDATE recipe_copy_operations SET {assignments} WHERE operation_id = ?",
                (*encoded.values(), operation_id),
            )
            connection.commit()

    @staticmethod
    def _to_model(row: sqlite3.Row) -> WebRecipeCopyOperation:
        snapshot = (
            json.loads(row["source_snapshot"]) if row["source_snapshot"] else None
        )
        completed = json.loads(row["completed_entry_ids"])
        result = json.loads(row["result_json"]) if row["result_json"] else None
        total = len(snapshot.get("ingredients", [])) if snapshot else None
        return WebRecipeCopyOperation(
            operation_id=row["operation_id"],
            status=row["status"],
            source_recipe_id=row["source_recipe_id"],
            target_title=row["target_title"],
            target_recipe_id=row["target_recipe_id"],
            completed_ingredient_count=len(completed),
            total_ingredient_count=total,
            retry_after=row["retry_after"],
            result=result,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class IdempotencyStore:
    """Durable response cache for synchronous create operations."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.RLock()
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_responses (
                    scope TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    status_code INTEGER,
                    response_json TEXT,
                    location TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (scope, idempotency_key)
                )
                """)
            connection.execute(
                """
                UPDATE idempotency_responses
                SET state = 'unknown',
                    error = 'facade restarted before the write was recorded',
                    updated_at = ?
                WHERE state = 'pending'
                """,
                (_utcnow().isoformat(),),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def begin(self, scope: str, key: str, payload: object) -> dict | None:
        if not 8 <= len(key) <= 255:
            raise ValueError(
                "Idempotency-Key must contain between 8 and 255 characters"
            )
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        request_hash = hashlib.sha256(serialized.encode()).hexdigest()
        now = _utcnow().isoformat()
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT * FROM idempotency_responses
                WHERE scope = ? AND idempotency_key = ?
                """,
                (scope, key),
            ).fetchone()
            if row is not None:
                if row["request_hash"] != request_hash:
                    raise FatsecretWebIdempotencyConflictError(
                        "idempotency key was already used for a different request"
                    )
                return dict(row)
            connection.execute(
                """
                INSERT INTO idempotency_responses (
                    scope, idempotency_key, request_hash, state,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (scope, key, request_hash, now, now),
            )
            connection.commit()
            return None

    def complete(
        self,
        scope: str,
        key: str,
        *,
        status_code: int,
        response: object,
        location: str | None = None,
    ) -> None:
        if hasattr(response, "model_dump"):
            response = response.model_dump(mode="json")
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                UPDATE idempotency_responses
                SET state = 'completed', status_code = ?, response_json = ?,
                    location = ?, error = NULL, updated_at = ?
                WHERE scope = ? AND idempotency_key = ?
                """,
                (
                    status_code,
                    json.dumps(response, sort_keys=True),
                    location,
                    _utcnow().isoformat(),
                    scope,
                    key,
                ),
            )
            connection.commit()

    def mark_unknown(self, scope: str, key: str, error: Exception) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                UPDATE idempotency_responses
                SET state = 'unknown', error = ?, updated_at = ?
                WHERE scope = ? AND idempotency_key = ?
                """,
                (str(error), _utcnow().isoformat(), scope, key),
            )
            connection.commit()


class RecipeCopyService:
    """Resumable, per-account recipe copy coordinator."""

    def __init__(
        self,
        client_factory: Callable[[], FatsecretWebClient],
        store: RecipeOperationStore,
        *,
        default_retry_after: int = 300,
        mutation_lock: threading.Lock | None = None,
        mutation_delay_seconds: float = 1.0,
    ) -> None:
        self._client_factory = client_factory
        self.store = store
        self.default_retry_after = default_retry_after
        self._mutation_lock = mutation_lock or threading.Lock()
        self.mutation_delay_seconds = mutation_delay_seconds

    def start_copy(
        self,
        source_recipe_id: int,
        target_title: str,
        idempotency_key: str,
    ) -> WebRecipeCopyOperation:
        if source_recipe_id <= 0:
            raise ValueError("source_recipe_id must be greater than zero")
        if not target_title.strip():
            raise ValueError("target_title must not be empty")
        return self.store.create_or_get(
            source_recipe_id=source_recipe_id,
            target_title=target_title.strip(),
            idempotency_key=idempotency_key,
        )

    def get_copy(self, operation_id: str) -> WebRecipeCopyOperation | None:
        return self.store.get(operation_id)

    def run_copy(self, operation_id: str) -> WebRecipeCopyOperation:
        """Run or resume a copy once; rate limits transition it to waiting."""

        with self._mutation_lock:
            raw = self.store.raw(operation_id)
            if raw is None:
                raise KeyError(operation_id)
            if raw["status"] == "completed":
                return self.store.get(operation_id)  # type: ignore[return-value]

            retry_after = (
                datetime.fromisoformat(raw["retry_after"])
                if raw["retry_after"]
                else None
            )
            if retry_after and retry_after > _utcnow():
                return self.store.get(operation_id)  # type: ignore[return-value]

            self.store.update(
                operation_id, status="running", error=None, retry_after=None
            )
            try:
                with self._client_factory() as client:
                    self._run_with_client(operation_id, client)
            except FatsecretWebRateLimitError as error:
                delay = error.retry_after or self.default_retry_after
                self.store.update(
                    operation_id,
                    status="waiting",
                    error=str(error),
                    retry_after=_utcnow() + timedelta(seconds=delay),
                )
            except FatsecretWebVerificationError as error:
                if error.retry_after is not None:
                    self.store.update(
                        operation_id,
                        status="waiting",
                        error=str(error),
                        retry_after=_utcnow()
                        + timedelta(
                            seconds=error.retry_after or self.default_retry_after
                        ),
                    )
                else:
                    self.store.update(operation_id, status="unknown", error=str(error))
            except Exception as error:
                self.store.update(operation_id, status="failed", error=str(error))
            return self.store.get(operation_id)  # type: ignore[return-value]

    def _run_with_client(self, operation_id: str, client: FatsecretWebClient) -> None:
        raw = self.store.raw(operation_id)
        if raw is None:
            raise KeyError(operation_id)
        source = (
            WebRecipeDetail.model_validate_json(raw["source_snapshot"])
            if raw["source_snapshot"]
            else client.get_recipe(raw["source_recipe_id"])
        )
        if raw["source_snapshot"] is None:
            self.store.update(operation_id, source_snapshot=source)

        if raw["target_recipe_id"] is None:
            pre_ids = (
                json.loads(raw["pre_create_recipe_ids"])
                if raw["pre_create_recipe_ids"]
                else [recipe.recipe_id for recipe in client.list_recipes()]
            )
            if raw["pre_create_recipe_ids"] is None:
                self.store.update(operation_id, pre_create_recipe_ids=pre_ids)
            candidates = [
                recipe
                for recipe in client.list_recipes()
                if recipe.recipe_id not in pre_ids
                and recipe.title == raw["target_title"]
            ]
            if len(candidates) > 1:
                raise FatsecretWebVerificationError(
                    "multiple possible copy targets appeared after an ambiguous create"
                )
            target = (
                client.get_recipe(candidates[0].recipe_id)
                if candidates
                else client.create_recipe(source.as_write(title=raw["target_title"]))
            )
            if not metadata_matches(target, source.as_write(title=raw["target_title"])):
                raise FatsecretWebVerificationError(
                    "reconciled copy target does not match the source metadata"
                )
            self.store.update(operation_id, target_recipe_id=target.recipe_id)
            target_id = target.recipe_id
        else:
            target_id = int(raw["target_recipe_id"])

        target = client.get_recipe(target_id)
        if not metadata_matches(target, source.as_write(title=raw["target_title"])):
            raise FatsecretWebVerificationError(
                f"copy target {target_id} metadata does not match source snapshot"
            )

        completed = self._reconcile_completed(source, target)
        self.store.update(operation_id, completed_entry_ids=completed)
        for ingredient in source.ingredients:
            if ingredient.entry_id in completed:
                continue
            if completed and self.mutation_delay_seconds:
                time.sleep(self.mutation_delay_seconds)
            client.add_recipe_ingredient(target_id, ingredient.as_write())
            completed.append(ingredient.entry_id)
            self.store.update(operation_id, completed_entry_ids=completed)

        result = client.get_recipe(target_id)
        if Counter(map(_ingredient_signature, result.ingredients)) != Counter(
            map(_ingredient_signature, source.ingredients)
        ):
            raise FatsecretWebVerificationError(
                f"copy target {target_id} ingredients do not match source snapshot"
            )
        self.store.update(
            operation_id,
            status="completed",
            completed_entry_ids=[item.entry_id for item in source.ingredients],
            result_json=result,
            error=None,
            retry_after=None,
        )

    @staticmethod
    def _reconcile_completed(
        source: WebRecipeDetail, target: WebRecipeDetail
    ) -> list[int]:
        available = Counter(map(_ingredient_signature, target.ingredients))
        expected = Counter(map(_ingredient_signature, source.ingredients))
        if available - expected:
            raise FatsecretWebVerificationError(
                "copy target contains ingredients not present in the source snapshot"
            )
        completed = []
        for ingredient in source.ingredients:
            signature = _ingredient_signature(ingredient)
            if available[signature] > 0:
                completed.append(ingredient.entry_id)
                available[signature] -= 1
        return completed


__all__ = ["IdempotencyStore", "RecipeCopyService", "RecipeOperationStore"]
