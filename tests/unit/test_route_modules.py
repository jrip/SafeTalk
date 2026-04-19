from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from fastapi import HTTPException

from app.core import ValidationError
from app.ml_models.constants import ML_MODEL_RUBERT_TOXICITY_ID
from app.ml_models.outcomes import ToxicityPrediction
from app.modules.billing import routes as billing_routes
from app.modules.history import routes as history_routes
from app.modules.neural import routes as neural_routes
from app.modules.users import routes as users_routes


def _register_verified_user_via_routes(
    app_container,
    *,
    email: str = "alice@example.com",
    password: str = "Secret123",
    name: str = "Alice",
) -> dict[str, Any]:
    registered = users_routes.register(
        users_routes.RegisterRequest(login=email, password=password, name=name),
        c=app_container,
    )
    users_routes.verify_email(
        users_routes.VerifyEmailRequest(login=email, code=registered["temporary_only_for_test_todo"]),
        c=app_container,
    )
    return registered


def test_register_route_rejects_invalid_email(app_container) -> None:
    invalid_payload = users_routes.RegisterRequest(
        login="invalid-email",
        password="Secret123",
        name="Alice",
    )
    with pytest.raises(ValidationError, match="Email format is invalid"):
        users_routes.register(invalid_payload, c=app_container)


def test_users_routes_register_verify_login_flow(app_container) -> None:
    registered = users_routes.register(
        users_routes.RegisterRequest(login="alice@example.com", password="Secret123", name="Alice"),
        c=app_container,
    )

    assert registered["name"] == "Alice"
    assert registered["role"] == "user"
    assert registered["identities"] == ["email:alice@example.com"]

    verify_result = users_routes.verify_email(
        users_routes.VerifyEmailRequest(
            login="alice@example.com",
            code=registered["temporary_only_for_test_todo"],
        ),
        c=app_container,
    )
    assert verify_result["status"] == "verified"

    login_result = users_routes.login(
        users_routes.LoginRequest(login="alice@example.com", password="Secret123"),
        c=app_container,
    )
    assert "access_token" in login_result


def test_users_routes_get_me_returns_profile(app_container) -> None:
    registered = _register_verified_user_via_routes(app_container)

    me = users_routes.get_me(c=app_container, current_user_id=registered["id"])
    assert me["id"] == registered["id"]
    assert me["identities"] == ["email:alice@example.com"]


def test_users_routes_update_me_updates_profile(app_container) -> None:
    registered = _register_verified_user_via_routes(app_container)

    updated = users_routes.update_me(
        users_routes.UpdateMeRequest(name="Alice Updated"),
        c=app_container,
        current_user_id=registered["id"],
    )
    assert updated["name"] == "Alice Updated"


def test_billing_routes_return_balance_and_ledger_for_owner(app_container, registered_user_factory) -> None:
    owner = registered_user_factory(email="owner@example.com")

    initial_balance = billing_routes.get_my_balance(c=app_container, current_user_id=owner.user.id)
    assert initial_balance["token_count"] == Decimal("0")

    topped_up = billing_routes.topup_me(
        billing_routes.TopUpRequest(amount=Decimal("15.00")),
        c=app_container,
        current_user_id=owner.user.id,
    )
    assert topped_up["token_count"] == Decimal("15.00")

    assert billing_routes.get_balance(owner.user.id, c=app_container, current_user_id=owner.user.id) == topped_up

    ledger = billing_routes.get_my_ledger(c=app_container, current_user_id=owner.user.id)
    assert len(ledger) == 1
    assert ledger[0]["kind"] == "credit"


def test_billing_routes_forbid_access_for_other_user(app_container, registered_user_factory) -> None:
    owner = registered_user_factory(email="owner@example.com")
    stranger = registered_user_factory(email="stranger@example.com")

    with pytest.raises(HTTPException) as exc_info:
        billing_routes.get_balance(owner.user.id, c=app_container, current_user_id=stranger.user.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied"


def test_history_routes_return_empty_list_for_owner(app_container, registered_user_factory) -> None:
    owner = registered_user_factory(email="owner@example.com")

    my_history = history_routes.my_history(c=app_container, current_user_id=owner.user.id)
    assert my_history == []


def test_history_routes_forbid_access_for_other_user(app_container, registered_user_factory) -> None:
    owner = registered_user_factory(email="owner@example.com")
    stranger = registered_user_factory(email="stranger@example.com")

    with pytest.raises(HTTPException) as exc_info:
        history_routes.history(owner.user.id, c=app_container, current_user_id=stranger.user.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied"


def test_neural_routes_list_models(
    app_container,
    registered_user_factory,
) -> None:
    user = registered_user_factory(email="predict@example.com")

    models = neural_routes.list_ml_models(c=app_container, _current_user_id=user.user.id)
    assert len(models) >= 1
    assert models[0]["id"] == ML_MODEL_RUBERT_TOXICITY_ID


def test_neural_routes_predict_and_get_task_lookup(
    app_container,
    registered_user_factory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = registered_user_factory(email="predict@example.com")
    app_container.billing.add_tokens(user.user.id, Decimal("50.00"))

    monkeypatch.setattr(
        "app.modules.neural.service.toxicity_predict",
        lambda text, model_id: ToxicityPrediction(
            summary="prediction-complete",
            is_toxic=False,
            toxicity_probability=0.125,
            breakdown={"toxicity": 0.125},
        ),
    )

    created = neural_routes.predict(
        neural_routes.PredictRequest(model_id=ML_MODEL_RUBERT_TOXICITY_ID, text="route prediction"),
        c=app_container,
        current_user_id=user.user.id,
    )
    assert "task_id" in created

    details = neural_routes.get_prediction_task(
        created["task_id"],
        c=app_container,
        current_user_id=user.user.id,
    )
    assert details["status"] == "completed"
    assert details["result_summary"] == "prediction-complete"
    assert details["charged_tokens"] == Decimal("16")


def test_route_containers_build_from_session(session) -> None:
    assert users_routes._container(session).users is not None
    assert billing_routes._container(session).billing is not None
    assert neural_routes._container(session).neural is not None
    assert history_routes._container(session).history is not None


def test_user_response_helpers_return_profile_payload(app_container, registered_user_factory) -> None:
    user = registered_user_factory(email="helper@example.com")

    billing_json = billing_routes._as_json(app_container.billing.get_count_tokens(user.user.id))
    assert billing_json["user_id"] == user.user.id

    user_json = users_routes._user_response_dict(app_container, user.user.id)
    assert user_json["id"] == user.user.id
    assert user_json["identities"] == ["email:helper@example.com"]
