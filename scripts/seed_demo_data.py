#!/usr/bin/env python3

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.types import now_utc
from app.db.database import SessionLocal
from app.modules.billing.models import BalanceLedgerEntryModel, UserBalanceModel
from app.modules.users.models import UserIdentityModel, UserModel
from app.modules.users.service import hash_password

DEMO_USER_ID = UUID("10000000-0000-4000-8000-000000000001")
DEMO_ADMIN_ID = UUID("10000000-0000-4000-8000-000000000002")
DEMO_USER_LOGIN = "demo@safetalk.local"
DEMO_ADMIN_LOGIN = "admin@safetalk.local"
DEMO_SEED_PASSWORD = "DemoPass123"

DEMO_LEDGER_CREDIT_USER_ID = UUID("20000000-0000-4000-8000-000000000004")
DEMO_LEDGER_CREDIT_ADMIN_ID = UUID("20000000-0000-4000-8000-000000000005")
DEMO_LEDGER_DEBIT_ADMIN_ID = UUID("20000000-0000-4000-8000-000000000007")


def _seed_demo_users(session) -> None:
    demos: tuple[dict, ...] = (
        {
            "id": DEMO_USER_ID,
            "login": DEMO_USER_LOGIN,
            "name": "Demo User",
            "role": "user",
            "credit_id": DEMO_LEDGER_CREDIT_USER_ID,
            "topup": Decimal("1000"),
        },
        {
            "id": DEMO_ADMIN_ID,
            "login": DEMO_ADMIN_LOGIN,
            "name": "Demo Admin",
            "role": "admin",
            "credit_id": DEMO_LEDGER_CREDIT_ADMIN_ID,
            "topup": Decimal("10000"),
        },
    )
    for demo in demos:
        exists = session.scalar(
            select(UserIdentityModel.id).where(
                UserIdentityModel.identity_type == "email",
                UserIdentityModel.identifier == demo["login"],
            )
        )
        if exists:
            continue
        session.add(
            UserModel(
                id=demo["id"],
                name=demo["name"],
                role=demo["role"],
            )
        )
        session.add(
            UserIdentityModel(
                user_id=demo["id"],
                identity_type="email",
                identifier=demo["login"],
                secret_hash=hash_password(DEMO_SEED_PASSWORD),
                is_verified=True,
            )
        )
        ts = now_utc()
        session.add(
            UserBalanceModel(
                user_id=demo["id"],
                token_count=demo["topup"],
                updated_at=ts,
            )
        )
        session.add(
            BalanceLedgerEntryModel(
                id=demo["credit_id"],
                user_id=demo["id"],
                kind="credit",
                amount=demo["topup"],
                task_id=None,
            )
        )
    session.flush()


def _seed_demo_admin_debit(session) -> None:
    if session.get(BalanceLedgerEntryModel, DEMO_LEDGER_DEBIT_ADMIN_ID) is not None:
        return
    if session.get(UserModel, DEMO_ADMIN_ID) is None:
        return
    balance = session.get(UserBalanceModel, DEMO_ADMIN_ID)
    if balance is None:
        return
    amount = Decimal("100")
    if balance.token_count < amount:
        return
    balance.token_count = balance.token_count - amount
    balance.updated_at = now_utc()
    session.add(
        BalanceLedgerEntryModel(
            id=DEMO_LEDGER_DEBIT_ADMIN_ID,
            user_id=DEMO_ADMIN_ID,
            kind="debit",
            amount=amount,
            task_id=None,
        )
    )
    session.flush()


def seed_demo_data(session) -> None:
    _seed_demo_users(session)
    _seed_demo_admin_debit(session)
    session.flush()


def main() -> None:
    session = SessionLocal()
    try:
        seed_demo_data(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
