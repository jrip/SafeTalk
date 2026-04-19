from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError as PydanticValidationError

from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID
from app.ml_models.outcomes import ToxicityPrediction
from app.modules.admin import routes as admin_routes
from app.modules.neural.types import RunPredictionInput
from app.modules.users.types import CreateUserInput


def _create_admin(app_container):
    admin = app_container.users.register(CreateUserInput(name="Admin", role="admin"))
    app_container.users.register_email_identity(admin.id, "admin@example.com", "AdminPass123")
    code = app_container.users.start_email_verification("admin@example.com")
    app_container.users.verify_email_code("admin@example.com", code)
    return admin


def _seed_completed_admin_visible_task(app_container, user_id, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "app.modules.neural.service.toxicity_predict",
        lambda text, model_id: ToxicityPrediction(
            summary="admin-visible-result",
            is_toxic=False,
            toxicity_probability=0.2,
            breakdown={"toxicity": 0.2},
        ),
    )
    app_container.billing.add_tokens(user_id, Decimal("40.00"))
    return app_container.neural.create_prediction_task(
        RunPredictionInput(
            user_id=user_id,
            model_id=ML_MODEL_RUBERT_TOXICITY_ID,
            text="admin route prediction",
        )
    )


def test_admin_request_model_requires_at_least_one_field() -> None:
    with pytest.raises(PydanticValidationError):
        admin_routes.AdminPatchUserRequest()


def test_admin_routes_enforce_access_for_non_admin(app_container, registered_user_factory) -> None:
    user = registered_user_factory(email="plain-user@example.com")

    with pytest.raises(HTTPException) as exc_info:
        admin_routes.admin_list_users(c=app_container, current_user_id=user.user.id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


def test_admin_can_list_and_get_user(
    app_container,
    registered_user_factory,
) -> None:
    admin = _create_admin(app_container)
    user = registered_user_factory(email="managed@example.com")

    listed_users = admin_routes.admin_list_users(c=app_container, current_user_id=admin.id)
    assert {row.id for row in listed_users} >= {admin.id, user.user.id}

    profile = admin_routes.admin_get_user(user.user.id, c=app_container, current_user_id=admin.id)
    assert profile["id"] == user.user.id
    assert profile["identities"] == ["email:managed@example.com"]


def test_admin_can_patch_user(app_container, registered_user_factory) -> None:
    admin = _create_admin(app_container)
    user = registered_user_factory(email="managed@example.com")

    patched = admin_routes.admin_patch_user(
        user.user.id,
        admin_routes.AdminPatchUserRequest(name="Managed Updated", allow_negative_balance=True),
        c=app_container,
        current_user_id=admin.id,
    )
    assert patched["name"] == "Managed Updated"
    assert patched["allow_negative_balance"] is True


def test_admin_can_manage_user_balance(app_container, registered_user_factory) -> None:
    admin = _create_admin(app_container)
    user = registered_user_factory(email="managed@example.com")

    topped_up = admin_routes.admin_topup_user(
        user.user.id,
        admin_routes.TopUpRequest(amount=Decimal("10.00")),
        c=app_container,
        current_user_id=admin.id,
    )
    assert topped_up["token_count"] == Decimal("10.00")

    spent = admin_routes.admin_spend_user(
        user.user.id,
        admin_routes.AdminSpendRequest(amount=Decimal("5.00")),
        c=app_container,
        current_user_id=admin.id,
    )
    assert spent["token_count"] == Decimal("5.00")


def test_admin_can_view_stats_history_and_task(app_container, registered_user_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _create_admin(app_container)
    user = registered_user_factory(email="managed@example.com")
    task = _seed_completed_admin_visible_task(app_container, user.user.id, monkeypatch)

    stats = admin_routes.admin_stats(c=app_container, current_user_id=admin.id)
    assert stats.users_count >= 2
    assert stats.admins_count >= 1
    assert stats.ml_tasks_total >= 1
    assert stats.ml_tasks_completed >= 1

    ledger = admin_routes.admin_ledger(c=app_container, current_user_id=admin.id, limit=5000)
    assert len(ledger) == 2

    history = admin_routes.admin_history(c=app_container, current_user_id=admin.id, limit=5000)
    assert len(history) == 1
    assert history[0]["result"] == "admin-visible-result"

    task_payload = admin_routes.admin_get_ml_task(task.task_id, c=app_container, current_user_id=admin.id)
    assert task_payload["task_id"] == task.task_id
    assert task_payload["status"] == "completed"
    assert task_payload["result_summary"] == "admin-visible-result"


def test_admin_user_profile_helper_returns_identities(app_container, registered_user_factory) -> None:
    admin = _create_admin(app_container)
    user = registered_user_factory(email="helper-admin@example.com")

    admin_routes._require_admin(app_container, admin.id)
    payload = admin_routes._user_profile_dict(app_container, user.user.id)

    assert payload["id"] == user.user.id
    assert payload["identities"] == ["email:helper-admin@example.com"]
