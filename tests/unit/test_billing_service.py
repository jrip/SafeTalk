from __future__ import annotations

from decimal import Decimal

import pytest

from app.core import InsufficientBalanceError
from app.modules.users.types import PatchUserInput


def test_add_tokens_updates_balance_and_ledger(app_container, registered_user_factory) -> None:
    registered_user = registered_user_factory()

    updated_balance = app_container.billing.add_tokens(registered_user.user.id, Decimal("25.50"))

    assert updated_balance.user_id == registered_user.user.id
    assert updated_balance.token_count == Decimal("25.50")

    ledger = app_container.billing.get_ledger_history(registered_user.user.id)
    assert len(ledger) == 1
    assert ledger[0].kind == "credit"
    assert ledger[0].amount == Decimal("25.50")
    assert ledger[0].task_id is None


def test_spend_tokens_rejects_overspend_without_negative_balance(app_container, registered_user_factory) -> None:
    registered_user = registered_user_factory()
    app_container.billing.add_tokens(registered_user.user.id, Decimal("10.00"))

    with pytest.raises(InsufficientBalanceError, match="Insufficient token balance"):
        app_container.billing.spend_tokens(registered_user.user.id, Decimal("10.01"))

    balance = app_container.billing.get_count_tokens(registered_user.user.id)
    ledger = app_container.billing.get_ledger_history(registered_user.user.id)

    assert balance.token_count == Decimal("10.00")
    assert len(ledger) == 1
    assert ledger[0].kind == "credit"


def test_spend_tokens_allows_negative_balance_when_enabled(app_container, registered_user_factory) -> None:
    registered_user = registered_user_factory()
    app_container.billing.add_tokens(registered_user.user.id, Decimal("5.00"))
    app_container.users.admin_patch_user(
        registered_user.user.id,
        PatchUserInput(allow_negative_balance=True),
    )

    updated_balance = app_container.billing.spend_tokens(registered_user.user.id, Decimal("8.00"))

    assert updated_balance.token_count == Decimal("-3.00")

    ledger = app_container.billing.get_ledger_history(registered_user.user.id)
    assert [entry.kind for entry in ledger] == ["debit", "credit"]
    assert ledger[0].amount == Decimal("8.00")
