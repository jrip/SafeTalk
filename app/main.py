from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from uuid import UUID

from fastapi import Depends, FastAPI
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.bootstrap import AppContainer, build_app_container
from app.core.settings import validate_settings
from app.db.config import Base  # подгружает модели в Base.metadata
from app.db.database import SessionLocal, engine, get_db
from app.db.seed import run_seed
from app.modules.neural.models import MlPredictionTaskModel
from app.modules.neural.types import RunPredictionInput
from app.modules.users.models import UserModel
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


def _user_view_from_db(session: Session, email: str) -> UserView | None:
    r = session.scalar(select(UserModel).where(UserModel.email == email.strip().lower()))
    if r is None:
        return None
    return UserView(
        id=r.id,
        email=r.email,
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
            u1 = c.users.register(CreateUserInput(email="startup-a@local", password_hash="x", name="Startup A"))
        except Exception:
            #Тут при каждом запуске это делается, поэтому просто игнор ошибки
            u1 = _user_view_from_db(session, "startup-a@local")
        try:
            u2 = c.users.register(CreateUserInput(email="startup-b@local", password_hash="x", name="Startup B"))
        except Exception:
            #Тут при каждом запуске это делается, поэтому просто игнор ошибки
            u2 = _user_view_from_db(session, "startup-b@local")

        try:
            if u1 is not None and u2 is not None:
                log.info("startup user1 %s", u1)
                log.info("startup user2 %s", u2)

                log.info("startup balance u1 (начало) %s", c.billing.get_count_tokens(u1.id))
                log.info("startup balance u2 (начало) %s", c.billing.get_count_tokens(u2.id))

                log.info("startup пополнение u1 %s", c.billing.add_tokens(u1.id, Decimal("500")))
                log.info("startup пополнение u2 %s", c.billing.add_tokens(u2.id, Decimal("500")))

                log.info("startup balance u1 после пополнения %s", c.billing.get_count_tokens(u1.id))
                log.info("startup balance u2 после пополнения %s", c.billing.get_count_tokens(u2.id))

                log.info("startup списание u1 %s", c.billing.spend_tokens(u1.id, Decimal("42")))

                log.info("startup balance u1 после списания %s", c.billing.get_count_tokens(u1.id))

                log.info(
                    "startup ml1 %s",
                    c.neural.create_prediction_task(
                        RunPredictionInput(user_id=u1.id, model_id=_ML_MODEL_ID, text="hello toxicity check"),
                    ),
                )
                log.info(
                    "startup ml2 %s",
                    c.neural.create_prediction_task(
                        RunPredictionInput(user_id=u2.id, model_id=_ML_MODEL_ID, text="another ml run"),
                    ),
                )

                log.info("startup balance u1 после ML %s", c.billing.get_count_tokens(u1.id))
                log.info("startup balance u2 после ML %s", c.billing.get_count_tokens(u2.id))

                log.info("startup журнал транзакций u1 %r", c.billing.get_ledger_history(u1.id))
                log.info("startup журнал транзакций u2 %r", c.billing.get_ledger_history(u2.id))

                log.info("startup history1 %r", c.history.get_api_history(u1.id))
                log.info("startup history2 %r", c.history.get_api_history(u2.id))
                tasks1 = session.scalars(
                    select(MlPredictionTaskModel).where(MlPredictionTaskModel.user_id == u1.id)
                ).all()
                tasks2 = session.scalars(
                    select(MlPredictionTaskModel).where(MlPredictionTaskModel.user_id == u2.id)
                ).all()
                log.info("startup tasks1 (%d)\n%s", len(tasks1), "\n".join(f"  {t}" for t in tasks1))
                log.info("startup tasks2 (%d)\n%s", len(tasks2), "\n".join(f"  {t}" for t in tasks2))
            else:
                log.warning("startup playbook skipped: users unresolved (u1=%r, u2=%r)", u1, u2)
        except Exception:
            log.exception("startup playbook failed")
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


app = FastAPI(title="SafeTalk", lifespan=lifespan)


def get_app_container(session: Session = Depends(get_db)) -> AppContainer:
    return build_app_container(session)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(session: Session = Depends(get_db)) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
