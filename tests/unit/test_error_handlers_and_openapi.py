from __future__ import annotations

from typing import Any

from fastapi import Body, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.api_models import ErrorResponse
from app.core.error_handlers import register_exception_handlers
from app.core.exceptions import DomainError, InsufficientBalanceError, NotFoundError, ValidationError
from app.core.public_openapi import public_openapi_from_full_schema


class Payload(BaseModel):
    name: str


class CustomDomainError(DomainError):
    pass


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/validation")
    def raise_validation() -> None:
        raise ValidationError("bad input")

    @app.get("/not-found")
    def raise_not_found() -> None:
        raise NotFoundError("missing object")

    @app.get("/insufficient")
    def raise_insufficient() -> None:
        raise InsufficientBalanceError("not enough credits")

    @app.get("/http-401")
    def raise_http_401() -> None:
        raise HTTPException(status_code=401, detail="no token", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/http-403")
    def raise_http_403() -> None:
        raise HTTPException(status_code=403, detail="denied")

    @app.get("/http-404")
    def raise_http_404() -> None:
        raise HTTPException(status_code=404, detail="gone")

    @app.get("/http-418")
    def raise_http_418() -> None:
        raise HTTPException(status_code=418, detail="teapot")

    @app.post("/request-validation")
    def request_validation(payload: Payload = Body(...)) -> dict[str, str]:
        return {"name": payload.name}

    @app.get("/domain")
    def raise_domain() -> None:
        raise CustomDomainError("generic domain failure")

    return app


def test_error_response_model_accepts_optional_details() -> None:
    payload = ErrorResponse(error="validation_error", message="boom", details={"field": "name"})

    assert payload.error == "validation_error"
    assert payload.message == "boom"
    assert payload.details == {"field": "name"}


def test_registered_error_handlers_return_expected_payloads() -> None:
    client = TestClient(_build_app())

    validation = client.get("/validation")
    assert validation.status_code == 400
    assert validation.json() == {"error": "validation_error", "message": "bad input"}

    not_found = client.get("/not-found")
    assert not_found.status_code == 404
    assert not_found.json() == {"error": "not_found", "message": "missing object"}

    insufficient = client.get("/insufficient")
    assert insufficient.status_code == 409
    assert insufficient.json() == {"error": "insufficient_balance", "message": "not enough credits"}

    unauthorized = client.get("/http-401")
    assert unauthorized.status_code == 401
    assert unauthorized.headers["www-authenticate"] == "Bearer"
    assert unauthorized.json() == {"error": "unauthorized", "message": "no token"}

    forbidden = client.get("/http-403")
    assert forbidden.status_code == 403
    assert forbidden.json() == {"error": "forbidden", "message": "denied"}

    gone = client.get("/http-404")
    assert gone.status_code == 404
    assert gone.json() == {"error": "not_found", "message": "gone"}

    teapot = client.get("/http-418")
    assert teapot.status_code == 418
    assert teapot.json() == {"error": "http_error", "message": "teapot"}

    request_validation = client.post("/request-validation", json={})
    assert request_validation.status_code == 422
    body = request_validation.json()
    assert body["error"] == "request_validation_error"
    assert body["message"] == "Invalid request payload"
    assert "fields" in body["details"]

    domain = client.get("/domain")
    assert domain.status_code == 400
    assert domain.json() == {"error": "domain_error", "message": "generic domain failure"}


def test_public_openapi_filters_internal_paths_and_prunes_unused_schemas() -> None:
    full_schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "SafeTalk"},
        "paths": {
            "/auth/login": {
                "post": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/LoginResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/balance/{user_id}": {
                "get": {
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PrivateBalanceResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/admin/stats": {"get": {"responses": {"200": {"description": "hidden"}}}},
            "/telegram/webhook": {"post": {"responses": {"200": {"description": "hidden"}}}},
            "/health": {"get": {"responses": {"200": {"description": "hidden"}}}},
        },
        "components": {
            "schemas": {
                "LoginResponse": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string"},
                        "profile": {"$ref": "#/components/schemas/PublicProfile"},
                    },
                },
                "PublicProfile": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
                "PrivateBalanceResponse": {
                    "type": "object",
                    "properties": {"amount": {"type": "string"}},
                },
                "UnusedSchema": {"type": "object"},
            }
        },
    }

    public_schema = public_openapi_from_full_schema(full_schema)

    assert set(public_schema["paths"]) == {"/auth/login"}
    assert set(public_schema["components"]["schemas"]) == {"LoginResponse", "PublicProfile"}
    assert "Публичная документация API SafeTalk" in public_schema["info"]["description"]
