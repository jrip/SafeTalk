from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_handlers import register_exception_handlers
from app.core.public_openapi import public_openapi_from_full_schema
from app.db.config import Base
from app.db.database import get_db
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID, ML_MODEL_TOXIC_LITE_ID
from app.modules.admin.routes import router as admin_router
from app.modules.billing.routes import router as balance_router
from app.modules.history.routes import router as history_router
from app.modules.neural.models import MlModelModel
from app.modules.neural.routes import router as predict_router
from app.modules.system.routes import router as system_router
from app.modules.users.auth import _token_to_user
from app.modules.users.routes import router as auth_router, users_router
import app.ml_models.service as ml_models_service
import app.modules.neural.service as neural_service_module
import app.modules.users.service as users_service_module


@dataclass(frozen=True)
class AuthSession:
    user_id: str
    access_token: str
    email: str
    password: str
    verification_code: str


def _build_test_app() -> FastAPI:
    app = FastAPI(
        title="SafeTalk Test",
        description=(
            "Test composition of SafeTalk routers with dependency overrides "
            "for integration scenarios."
        ),
    )
    register_exception_handlers(app)
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(balance_router)
    app.include_router(predict_router)
    app.include_router(history_router)
    app.include_router(admin_router)

    @app.get("/openapi-public.json", include_in_schema=False)
    def openapi_public_json() -> JSONResponse:
        return JSONResponse(public_openapi_from_full_schema(app.openapi()))

    @app.get("/docs-public", include_in_schema=False)
    def docs_public() -> HTMLResponse:
        return HTMLResponse("<html><body><h1>SafeTalk Test Docs</h1></body></html>")

    return app


@pytest.fixture(autouse=True)
def stubbed_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        users_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            email_verification_ttl_seconds=3600,
            email_verification_max_attempts=3,
        ),
    )
    monkeypatch.setattr(
        neural_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            ml_max_dialog_chars=4096,
            rabbitmq_url=None,
        ),
    )
    monkeypatch.setattr(
        ml_models_service,
        "get_settings",
        lambda: SimpleNamespace(
            ml_toxicity_backend="mock",
            ml_toxicity_max_length=384,
        ),
    )


@pytest.fixture(autouse=True)
def clear_token_store() -> None:
    _token_to_user.clear()


@pytest.fixture(autouse=True)
def stub_toxicity_predict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.modules.neural.service.toxicity_predict",
        lambda text, model_id: ml_models_service.ToxicityPrediction(
            summary=f"predicted:{text}",
            is_toxic=False,
            toxicity_probability=0.125,
            breakdown={"toxicity": 0.125},
        ),
    )


@pytest.fixture
def session_factory() -> Generator[sessionmaker, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with factory() as session:
        session.add_all(
            [
                MlModelModel(
                    id=ML_MODEL_RUBERT_TOXICITY_ID,
                    slug="toxic-baseline",
                    name="Baseline toxicity",
                    description="Default toxicity model for integration tests",
                    version="1.0.0",
                    is_active=True,
                    is_default=True,
                    price_per_character=Decimal("1.00"),
                ),
                MlModelModel(
                    id=ML_MODEL_TOXIC_LITE_ID,
                    slug="toxic-lite",
                    name="Lite toxicity",
                    description="Unsupported lite model for integration tests",
                    version="1.0.0",
                    is_active=True,
                    is_default=False,
                    price_per_character=Decimal("0.50"),
                ),
            ]
        )
        session.commit()

    yield factory

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def app(session_factory: sessionmaker) -> FastAPI:
    app = _build_test_app()

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def client_factory(app: FastAPI) -> Callable[..., TestClient]:
    def _build(*, raise_server_exceptions: bool = True) -> TestClient:
        return TestClient(app, raise_server_exceptions=raise_server_exceptions)

    return _build


@pytest.fixture
def auth_headers() -> Callable[[str], dict[str, str]]:
    def _build(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _build


@pytest.fixture
def register_and_login(client: TestClient) -> Callable[..., AuthSession]:
    def _register_and_login(
        *,
        email: str | None = None,
        password: str = "StrongPass123",
        name: str = "Integration User",
    ) -> AuthSession:
        login = email or f"user-{uuid4().hex}@example.com"
        register_response = client.post(
            "/auth/register",
            json={"login": login, "password": password, "name": name},
        )
        assert register_response.status_code == 201, register_response.text
        register_payload = register_response.json()
        verification_code = register_payload["temporary_only_for_test_todo"]

        verify_response = client.post(
            "/auth/verify-email",
            json={"login": login, "code": verification_code},
        )
        assert verify_response.status_code == 200, verify_response.text

        login_response = client.post(
            "/auth/login",
            json={"login": login, "password": password},
        )
        assert login_response.status_code == 200, login_response.text

        return AuthSession(
            user_id=register_payload["id"],
            access_token=login_response.json()["access_token"],
            email=login,
            password=password,
            verification_code=verification_code,
        )

    return _register_and_login
