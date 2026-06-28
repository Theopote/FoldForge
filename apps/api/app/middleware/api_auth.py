"""API key middleware for protected routes."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.auth import api_auth_enabled, extract_api_key, is_valid_api_key, path_requires_api_auth


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Require a valid API key on /api/* and /storage/* when configured."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        if not api_auth_enabled() or not path_requires_api_auth(request.url.path):
            return await call_next(request)

        if not is_valid_api_key(extract_api_key(request)):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
