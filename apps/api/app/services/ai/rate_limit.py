"""Per-client rate limiting for paid AI generation endpoints."""

from __future__ import annotations

import hashlib
import math
import time

from fastapi import HTTPException, Request, status

from app.auth import extract_api_key
from app.config import settings


class AiGenerationRateLimiter:
    """SQLite-backed token bucket for /api/generate-from-* cost control."""

    _SCOPE = "ai_generation"

    def __init__(
        self,
        *,
        capacity: float,
        refill_per_sec: float,
    ) -> None:
        self._capacity = capacity
        self._refill_per_sec = refill_per_sec

    def try_acquire(self, bucket_key: str, *, cost: float = 1.0) -> int | None:
        """
        Consume one token when allowed.

        Returns None on success, or seconds until retry when rate limited.
        """
        now = time.time()
        storage_key = f"{self._SCOPE}:{bucket_key}"

        from app.db.database import database

        with database.connection() as conn:
            row = conn.execute(
                """
                SELECT tokens, updated_at
                FROM rate_limit_buckets
                WHERE bucket_key = ?
                """,
                (storage_key,),
            ).fetchone()

            if row is None:
                tokens = self._capacity
                updated_at = now
            else:
                tokens = float(row["tokens"])
                updated_at = float(row["updated_at"])

            elapsed = max(0.0, now - updated_at)
            tokens = min(self._capacity, tokens + elapsed * self._refill_per_sec)

            if tokens < cost:
                if self._refill_per_sec <= 0:
                    retry_after = 3600
                else:
                    retry_after = max(
                        1,
                        int(math.ceil((cost - tokens) / self._refill_per_sec)),
                    )
                conn.execute(
                    """
                    INSERT INTO rate_limit_buckets (bucket_key, tokens, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(bucket_key) DO UPDATE SET
                        tokens = excluded.tokens,
                        updated_at = excluded.updated_at
                    """,
                    (storage_key, tokens, now),
                )
                return retry_after

            tokens -= cost
            conn.execute(
                """
                INSERT INTO rate_limit_buckets (bucket_key, tokens, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(bucket_key) DO UPDATE SET
                    tokens = excluded.tokens,
                    updated_at = excluded.updated_at
                """,
                (storage_key, tokens, now),
            )
            return None


def rate_limit_bucket_key(request: Request) -> str:
    """Derive a stable per-client bucket id from API key or client IP."""
    api_key = extract_api_key(request)
    if api_key:
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]
        return f"apikey:{digest}"

    client = request.client
    host = client.host if client else "unknown"
    return f"ip:{host}"


def should_apply_ai_generation_rate_limit(provider_name: str) -> bool:
    if not settings.ai_generation_rate_limit_enabled:
        return False
    if provider_name == "mock":
        return False
    return True


def _limiter() -> AiGenerationRateLimiter:
    per_hour = max(1, settings.ai_generation_rate_limit_per_hour)
    burst = max(1, settings.ai_generation_rate_limit_burst)
    return AiGenerationRateLimiter(
        capacity=float(burst),
        refill_per_sec=per_hour / 3600.0,
    )


def enforce_ai_generation_rate_limit(request: Request, provider_name: str) -> None:
    """Raise HTTP 429 when the client exceeds the AI generation quota."""
    if not should_apply_ai_generation_rate_limit(provider_name):
        return

    bucket_key = rate_limit_bucket_key(request)
    retry_after = _limiter().try_acquire(bucket_key)
    if retry_after is None:
        return

    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=(
            "AI generation rate limit exceeded. "
            f"Try again in {retry_after} seconds."
        ),
        headers={"Retry-After": str(retry_after)},
    )
