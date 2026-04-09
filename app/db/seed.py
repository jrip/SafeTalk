from __future__ import annotations

import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.types import now_utc
from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
from app.modules.users.passwords import hash_password
from app.modules.feedback.models import FeedbackModel
from app.modules.history.models import HistoryRecordModel
from app.modules.neural.models import MlModelModel, MlPredictionTaskModel
from app.modules.users.models import UserIdentityModel, UserModel

_ML_MODEL_SPECS: tuple[dict, ...] = (
    {
        "id": UUID("00000000-0000-4000-8000-000000000001"),
        "slug": "toxic-baseline",
        "name": "Toxicity baseline",
        "description": "Базовая модель токсичности для демо.",
        "version": "1.0.0",
        "is_active": True,
        "is_default": True,
        "price_per_character": Decimal("0.01"),
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000002"),
        "slug": "toxic-lite",
        "name": "Toxicity lite",
        "description": "Облегчённая модель (дешевле за запрос).",
        "version": "1.0.0",
        "is_active": True,
        "is_default": False,
        "price_per_character": Decimal("0.005"),
    },
)

_DEFAULT_ML_MODEL_ID = UUID("00000000-0000-4000-8000-000000000001")

_DEMO_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
_DEMO_ADMIN_ID = UUID("10000000-0000-4000-8000-000000000002")
_DEMO_USER_LOGIN = "demo@safetalk.local"
_DEMO_ADMIN_LOGIN = "admin@safetalk.local"
# Один пароль для демо-юзера и админа (bcrypt в БД; логины см. выше).
_DEMO_SEED_PASSWORD = "DemoPass123"

_DEMO_TASK_ID = UUID("20000000-0000-4000-8000-000000000001")
_DEMO_HISTORY_ID = UUID("20000000-0000-4000-8000-000000000002")
_DEMO_LEDGER_DEBIT_ID = UUID("20000000-0000-4000-8000-000000000003")
_DEMO_LEDGER_CREDIT_USER_ID = UUID("20000000-0000-4000-8000-000000000004")
_DEMO_LEDGER_CREDIT_ADMIN_ID = UUID("20000000-0000-4000-8000-000000000005")
_DEMO_FEEDBACK_ID = UUID("20000000-0000-4000-8000-000000000006")
_DEMO_LEDGER_DEBIT_ADMIN_ID = UUID("20000000-0000-4000-8000-000000000007")


def _seed_ml_models(session: Session) -> None:
    for spec in _ML_MODEL_SPECS:
        slug = spec["slug"]
        if session.scalar(select(MlModelModel.id).where(MlModelModel.slug == slug)):
            continue
        session.add(MlModelModel(**spec))
    session.flush()


def _seed_demo_users(session: Session) -> None:
    """Демо-аккаунты для Swagger / проверок.

    demo@safetalk.local / DemoPass123 — обычный пользователь.
    admin@safetalk.local / DemoPass123 — админ (topup, просмотр чужих профилей при необходимости).
    """
    demos: tuple[dict, ...] = (
        {
            "id": _DEMO_USER_ID,
            "login": _DEMO_USER_LOGIN,
            "name": "Demo User",
            "role": "user",
            "credit_id": _DEMO_LEDGER_CREDIT_USER_ID,
            "topup": Decimal("1000"),
        },
        {
            "id": _DEMO_ADMIN_ID,
            "login": _DEMO_ADMIN_LOGIN,
            "name": "Demo Admin",
            "role": "admin",
            "credit_id": _DEMO_LEDGER_CREDIT_ADMIN_ID,
            "topup": Decimal("10000"),
        },
    )
    for d in demos:
        if session.scalar(
            select(UserIdentityModel.id).where(
                UserIdentityModel.identity_type == "email",
                UserIdentityModel.identifier == d["login"],
            )
        ):
            continue
        session.add(
            UserModel(
                id=d["id"],
                name=d["name"],
                role=d["role"],
            )
        )
        session.add(
            UserIdentityModel(
                user_id=d["id"],
                identity_type="email",
                identifier=d["login"],
                secret_hash=hash_password(_DEMO_SEED_PASSWORD),
                is_verified=True,
            )
        )
        ts = now_utc()
        session.add(
            UserBalanceModel(
                user_id=d["id"],
                token_count=d["topup"],
                updated_at=ts,
            )
        )
        session.add(
            BalanceLedgerEntryModel(
                id=d["credit_id"],
                user_id=d["id"],
                kind="credit",
                amount=d["topup"],
                task_id=None,
            )
        )
    session.flush()


def _seed_demo_user_rich_data(session: Session) -> None:
    if session.get(MlPredictionTaskModel, _DEMO_TASK_ID) is not None:
        return
    if session.get(UserModel, _DEMO_USER_ID) is None:
        return

    demo_text = "Sample demo text for SafeTalk."
    price = Decimal("0.01")
    charge = Decimal(len(demo_text)) * price

    bal = session.get(UserBalanceModel, _DEMO_USER_ID)
    if bal is None:
        return
    if bal.token_count < charge:
        return

    ts = now_utc()
    session.add(
        MlPredictionTaskModel(
            id=_DEMO_TASK_ID,
            user_id=_DEMO_USER_ID,
            model_id=_DEFAULT_ML_MODEL_ID,
            text=demo_text,
            status="pending",
            charged_tokens=charge,
        )
    )
    session.add(
        HistoryRecordModel(
            id=_DEMO_HISTORY_ID,
            user_id=_DEMO_USER_ID,
            ml_model_id=_DEFAULT_ML_MODEL_ID,
            ml_task_id=_DEMO_TASK_ID,
            request=demo_text,
            result="PENDING",
            tokens_charged=charge,
        )
    )
    session.add(
        BalanceLedgerEntryModel(
            id=_DEMO_LEDGER_DEBIT_ID,
            user_id=_DEMO_USER_ID,
            kind="debit",
            amount=charge,
            task_id=_DEMO_TASK_ID,
        )
    )
    bal.token_count = bal.token_count - charge
    bal.updated_at = ts

    session.add(
        FeedbackModel(
            id=_DEMO_FEEDBACK_ID,
            history_id=_DEMO_HISTORY_ID,
            user_id=_DEMO_USER_ID,
            is_toxic=False,
            comment="seed demo feedback",
        )
    )
    session.flush()


def _seed_demo_admin_debit(session: Session) -> None:
    """Ручное списание в демо-данных (админ): пополнение уже в _seed_demo_users."""
    if session.get(BalanceLedgerEntryModel, _DEMO_LEDGER_DEBIT_ADMIN_ID) is not None:
        return
    if session.get(UserModel, _DEMO_ADMIN_ID) is None:
        return
    bal = session.get(UserBalanceModel, _DEMO_ADMIN_ID)
    if bal is None:
        return
    amount = Decimal("100")
    if bal.token_count < amount:
        return
    ts = now_utc()
    session.add(
        BalanceLedgerEntryModel(
            id=_DEMO_LEDGER_DEBIT_ADMIN_ID,
            user_id=_DEMO_ADMIN_ID,
            kind="debit",
            amount=amount,
            task_id=None,
        )
    )
    bal.token_count = bal.token_count - amount
    bal.updated_at = ts
    session.flush()


def run_seed(session: Session) -> None:
    """Идемпотентно: ML-модели, демо-пользователь и админ, балансы, журнал, пример задачи/истории/фидбека."""
    _seed_ml_models(session)
    _seed_demo_users(session)
    _seed_demo_admin_debit(session)
    _seed_demo_user_rich_data(session)
    session.flush()
