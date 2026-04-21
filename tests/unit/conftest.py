from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.bootstrap import AppContainer, build_app_container
from app.db.config import Base
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID, ML_MODEL_TOXIC_LITE_ID
from app.modules.neural.models import MlModelModel
from app.modules.users.types import CreateUserInput, UserView
import app.ml_models.service as ml_models_service
import app.modules.neural.service as neural_service_module
import app.modules.users.service as users_service_module


@dataclass(frozen=True)
class RegisteredUser:
    user: UserView
    email: str
    password: str


@pytest.fixture(autouse=True)
def stubbed_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        users_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            email_verification_ttl_seconds=3600,
            email_verification_max_attempts=3,
            password_reset_ttl_seconds=3600,
            password_reset_max_per_email_per_hour=10,
            password_reset_public_base_url=None,
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


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    Base.metadata.create_all(engine)

    with session_factory() as db_session:
        db_session.add_all(
            [
                MlModelModel(
                    id=ML_MODEL_RUBERT_TOXICITY_ID,
                    slug="toxic-baseline",
                    name="Baseline toxicity",
                    description="Default toxicity model for tests",
                    version="1.0.0",
                    is_active=True,
                    is_default=True,
                    price_per_character=Decimal("1.00"),
                ),
                MlModelModel(
                    id=ML_MODEL_TOXIC_LITE_ID,
                    slug="toxic-lite",
                    name="Lite toxicity",
                    description="Unsupported lite model for tests",
                    version="1.0.0",
                    is_active=True,
                    is_default=False,
                    price_per_character=Decimal("0.50"),
                ),
            ]
        )
        db_session.commit()
        yield db_session

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def app_container(session: Session) -> AppContainer:
    return build_app_container(session)


@pytest.fixture
def registered_user_factory(app_container: AppContainer) -> Callable[..., RegisteredUser]:
    def _create(*, name: str = "Test User", email: str | None = None, password: str = "StrongPass123") -> RegisteredUser:
        login = email or f"user-{uuid4().hex}@example.com"
        user = app_container.users.register(CreateUserInput(name=name))
        app_container.users.register_email_identity(user.id, login, password)
        verification_code = app_container.users.start_email_verification(login)
        app_container.users.verify_email_code(login, verification_code)
        return RegisteredUser(user=user, email=login, password=password)

    return _create
