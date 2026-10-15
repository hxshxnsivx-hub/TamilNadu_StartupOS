"""Request-context and rate-limit middleware (Task 1.9.7).

The rate limiter here is a simple in-process sliding-window guard suitable for
local dev and a single worker. Task 5.5 replaces it with a Redis-backed limiter
that holds across horizontally-scaled workers.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to every request and echo it as a response header."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-process per-client + global sliding-window limiter (60s window)."""

    def __init__(self, app, per_user_per_min: int, global_per_min: int) -> None:
        super().__init__(app)
        self.per_user = per_user_per_min
        self.global_limit = global_per_min
        self._per_client: dict[str, deque[float]] = defaultdict(deque)
        self._global: deque[float] = deque()

    @staticmethod
    def _client_key(request: Request) -> str:
        # Prefer authenticated subject when available; fall back to client host.
        subject = getattr(request.state, "user_id", None)
        if subject:
            return f"user:{subject}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    @staticmethod
    def _trim(window: deque[float], now: float) -> None:
        cutoff = now - 60.0
        while window and window[0] < cutoff:
            window.popleft()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        now = time.monotonic()
        self._trim(self._global, now)
        if len(self._global) >= self.global_limit:
            return self._limited(request)

        key = self._client_key(request)
        window = self._per_client[key]
        self._trim(window, now)
        if len(window) >= self.per_user:
            return self._limited(request)

        window.append(now)
        self._global.append(now)
        return await call_next(request)

    @staticmethod
    def _limited(request: Request) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        return JSONResponse(
            status_code=429,
            content={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "error_message": "Too many requests — please slow down.",
                "error_details": None,
                "timestamp": "",
                "request_id": request_id,
                "suggestions": ["Retry after a minute."],
            },
            headers={"retry-after": "60"},
        )
