"""Shared API key authentication helpers."""

from __future__ import annotations

import secrets

from fastapi import HTTPException, Request, status

from app.config import settings


def api_auth_enabled() -> bool:
    """Return True when requests must present a valid API key."""
    return bool(settings.api_key)


def path_requires_api_auth(path: str) -> bool:
    return path.startswith("/api/") or path.startswith("/storage/")


def extract_api_key(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            return token

    header_key = request.headers.get("X-API-Key")
    if header_key and header_key.strip():
        return header_key.strip()

    query_token = request.query_params.get("access_token")
    if query_token and query_token.strip():
        return query_token.strip()

    return None


def is_valid_api_key(provided: str | None) -> bool:
    expected = settings.api_key
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided, expected)


def verify_api_key(request: Request) -> None:
    """Raise HTTP 401 when auth is enabled and the request key is missing/invalid."""
    if not api_auth_enabled():
        return
    if not is_valid_api_key(extract_api_key(request)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
