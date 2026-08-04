"""Standardized error response + exception handlers (design.md Error Handling)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorResponse(BaseModel):
    """Machine- and human-readable error envelope (design.md §Error Handling)."""

    error_code: str
    error_message: str
    error_details: dict | None = None
    timestamp: str
    request_id: str
    suggestions: list[str] | None = None


class AppError(Exception):
    """Base domain error carrying a stable code and optional recovery suggestions."""

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.suggestions = suggestions


def _envelope(
    request: Request,
    *,
    code: str,
    message: str,
    details: dict | None = None,
    suggestions: list[str] | None = None,
) -> ErrorResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    return ErrorResponse(
        error_code=code,
        error_message=message,
        error_details=details,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request_id=request_id,
        suggestions=suggestions,
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        env = _envelope(
            request,
            code=exc.error_code,
            message=exc.message,
            details=exc.details,
            suggestions=exc.suggestions,
        )
        return JSONResponse(status_code=exc.status_code, content=env.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        env = _envelope(
            request,
            code="VALIDATION_FAILED",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=env.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        env = _envelope(
            request,
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
        )
        return JSONResponse(status_code=exc.status_code, content=env.model_dump())

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        env = _envelope(
            request,
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        )
        return JSONResponse(status_code=500, content=env.model_dump())
