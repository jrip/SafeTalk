from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status

from app.core.exceptions import DomainError, InsufficientBalanceError, NotFoundError, ValidationError


def _error_payload(error: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": error,
        "message": message,
    }
    if details:
        payload["details"] = details
    return payload


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def handle_validation_error(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_payload("validation_error", str(exc)),
        )

    @app.exception_handler(NotFoundError)
    async def handle_not_found_error(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_payload("not_found", str(exc)),
        )

    @app.exception_handler(InsufficientBalanceError)
    async def handle_insufficient_balance(_: Request, exc: InsufficientBalanceError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_payload("insufficient_balance", str(exc)),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_payload(
                "request_validation_error",
                "Invalid request payload",
                {"fields": exc.errors()},
            ),
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        error_code = "http_error"
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "unauthorized"
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "forbidden"
        elif exc.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "not_found"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(error_code, str(exc.detail)),
            headers=exc.headers,
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_payload("domain_error", str(exc)),
        )
