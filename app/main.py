from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bootstrap import AppContainer, build_app_container
from app.core.error_handlers import register_exception_handlers
from app.core.settings import validate_settings
from app.db.config import Base  # подгружает модели в Base.metadata
from app.db.database import SessionLocal, engine
from app.modules.billing.routes import router as balance_router
from app.modules.history.routes import router as history_router
from app.modules.neural.routes import router as predict_router
from app.modules.system.routes import router as system_router
from app.modules.telegram.routes import router as telegram_router
from app.modules.users.routes import router as auth_router, users_router
from app.db.seed import run_seed
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.types import RunPredictionInput
from app.modules.users.models import UserIdentityModel, UserModel
from app.modules.users.types import CreateUserInput, UserView


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
        force=True,
    )


_configure_logging()
log = logging.getLogger(__name__)

_ML_MODEL_ID = UUID("00000000-0000-4000-8000-000000000001")


def _user_view_from_db(session: Session, login: str) -> UserView | None:
    identity = session.scalar(
        select(UserIdentityModel).where(
            UserIdentityModel.identity_type == "email",
            UserIdentityModel.identifier == login.strip().lower(),
        )
    )
    if identity is None:
        return None
    r = session.get(UserModel, identity.user_id)
    if r is None:
        return None
    return UserView(
        id=r.id,
        name=r.name,
        role=r.role,
        allow_negative_balance=r.allow_negative_balance,
    )


def _init_db_schema_and_seed() -> None:
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        run_seed(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _startup_playbook() -> None:
    session = SessionLocal()
    try:
        c: AppContainer = build_app_container(session)

        u1: UserView | None = None
        u2: UserView | None = None
        try:
            u1 = c.users.register(CreateUserInput(name="Startup A"))
            c.users.register_email_identity(u1.id, "startup-a@local", "x")
        except Exception:
            #Тут при каждом запуске это делается, поэтому просто игнор ошибки
            u1 = _user_view_from_db(session, "startup-a@local")
        try:
            u2 = c.users.register(CreateUserInput(name="Startup B"))
            c.users.register_email_identity(u2.id, "startup-b@local", "x")
        except Exception:
            #Тут при каждом запуске это делается, поэтому просто игнор ошибки
            u2 = _user_view_from_db(session, "startup-b@local")

        try:
            if u1 is not None and u2 is not None:
                log.info("Пользователь 1: %s", u1)
                log.info("Пользователь 2: %s", u2)

                spend_amount = Decimal("42")
                topup_amount = Decimal("500")

                log.info("u1 баланс: %s", c.billing.get_count_tokens(u1.id).token_count)
                log.info("u1 списываю: %s", spend_amount)
                log.info("u1 стало: %s", c.billing.spend_tokens(u1.id, spend_amount).token_count)
                log.info("u1 добавляю: %s", topup_amount)
                log.info("u1 стало: %s", c.billing.add_tokens(u1.id, topup_amount).token_count)

                log.info("u2 баланс: %s", c.billing.get_count_tokens(u2.id).token_count)
                log.info("u2 списываю: %s", spend_amount)
                log.info("u2 стало: %s", c.billing.spend_tokens(u2.id, spend_amount).token_count)
                log.info("u2 добавляю: %s", topup_amount)
                log.info("u2 стало: %s", c.billing.add_tokens(u2.id, topup_amount).token_count)

                ml1 = c.neural.create_prediction_task(
                    RunPredictionInput(user_id=u1.id, model_id=_ML_MODEL_ID, text="hello toxicity check"),
                )
                log.info("u1 ML-задача создана: task_id=%s, цена=%s", ml1.task_id, ml1.charged_tokens)
                log.info("u1 баланс после ML: %s", c.billing.get_count_tokens(u1.id).token_count)

                ml2 = c.neural.create_prediction_task(
                    RunPredictionInput(user_id=u2.id, model_id=_ML_MODEL_ID, text="another ml run"),
                )
                log.info("u2 ML-задача создана: task_id=%s, цена=%s", ml2.task_id, ml2.charged_tokens)
                log.info("u2 баланс после ML: %s", c.billing.get_count_tokens(u2.id).token_count)

                log.info("Журнал транзакций u1: %r", c.billing.get_ledger_history(u1.id))
                log.info("Журнал транзакций u2: %r", c.billing.get_ledger_history(u2.id))

                log.info("История запросов u1: %r", c.history.get_api_history(u1.id))
                log.info("История запросов u2: %r", c.history.get_api_history(u2.id))
                tasks1 = session.scalars(
                    select(MlPredictionTaskModel).where(MlPredictionTaskModel.user_id == u1.id)
                ).all()
                tasks2 = session.scalars(
                    select(MlPredictionTaskModel).where(MlPredictionTaskModel.user_id == u2.id)
                ).all()
                log.info("Список ML-задач u1 (%d)\n%s", len(tasks1), "\n".join(f"  {t}" for t in tasks1))
                log.info("Список ML-задач u2 (%d)\n%s", len(tasks2), "\n".join(f"  {t}" for t in tasks2))
            else:
                log.warning("Сценарий пропущен: пользователи не определены (u1=%r, u2=%r)", u1, u2)
        except Exception:
            log.exception("Ошибка при выполнении сценария на старте")
            session.rollback()
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()
    validate_settings()
    await asyncio.to_thread(_init_db_schema_and_seed)
    await asyncio.to_thread(_startup_playbook)
    yield


app = FastAPI(
    title="SafeTalk",
    lifespan=lifespan,
    description=(
        "Для защищённых ручек нажми **Authorize** (замок вверху страницы /docs), "
        "вставь только токен из `POST /auth/login` без префикса `Bearer`."
    ),
    swagger_ui_parameters={
        "persistAuthorization": True,
        "tryItOutEnabled": True,
    },
)
register_exception_handlers(app)
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(telegram_router)
app.include_router(users_router)
app.include_router(balance_router)
app.include_router(predict_router)
app.include_router(history_router)
