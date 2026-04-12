from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.types import now_utc
from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
from app.modules.users.service import hash_password
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID, ML_MODEL_TOXIC_LITE_ID
from app.modules.neural.models import MlModelModel
from app.modules.users.models import UserIdentityModel, UserModel

_ML_MODEL_SPECS: tuple[dict, ...] = (
    {
        "id": ML_MODEL_RUBERT_TOXICITY_ID,
        "slug": "toxic-baseline",
        "name": "RuBERT-tiny toxicity",
        "description": "Multilabel токсичность (HF cointegrated/rubert-tiny-toxicity), русский чат.",
        "version": "1.0.0",
        "is_active": True,
        "is_default": True,
        "price_per_character": Decimal("1.00"),
    },
    {
        "id": ML_MODEL_TOXIC_LITE_ID,
        "slug": "toxic-lite",
        "name": "Toxicity lite",
        "description": "Облегчённая модель (дешевле за запрос); инференс в API пока не подключён.",
        "version": "1.0.0",
        "is_active": True,
        "is_default": False,
        "price_per_character": Decimal("0.50"),
    },
)

_DEMO_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
_DEMO_ADMIN_ID = UUID("10000000-0000-4000-8000-000000000002")
_DEMO_USER_LOGIN = "demo@safetalk.local"
_DEMO_ADMIN_LOGIN = "admin@safetalk.local"
# Один пароль для демо-юзера и админа (bcrypt в БД; логины см. выше).
_DEMO_SEED_PASSWORD = "DemoPass123"

_DEMO_LEDGER_CREDIT_USER_ID = UUID("20000000-0000-4000-8000-000000000004")
_DEMO_LEDGER_CREDIT_ADMIN_ID = UUID("20000000-0000-4000-8000-000000000005")
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
    """Идемпотентно: ML-модели, демо-пользователь и админ, балансы, журнал."""
    _seed_ml_models(session)
    _seed_demo_users(session)
    _seed_demo_admin_debit(session)
    session.flush()
