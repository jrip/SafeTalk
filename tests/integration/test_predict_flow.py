from __future__ import annotations

from decimal import Decimal

import pytest


def test_predict_success_updates_balance_and_history(client, auth_headers, register_and_login) -> None:
    session = register_and_login(email="predict-success@example.com")
    headers = auth_headers(session.access_token)

    topup_response = client.post("/balance/me/topup", headers=headers, json={"amount": "30.00"})
    assert topup_response.status_code == 200
    assert Decimal(topup_response.json()["token_count"]) == Decimal("30.00")

    models_response = client.get("/predict/models", headers=headers)
    assert models_response.status_code == 200
    models_payload = models_response.json()
    assert len(models_payload) >= 1
    model_id = models_payload[0]["id"]

    predict_response = client.post(
        "/predict",
        headers=headers,
        json={"model_id": model_id, "text": "integration ml run"},
    )
    assert predict_response.status_code == 200
    task_id = predict_response.json()["task_id"]

    task_response = client.get(f"/predict/{task_id}", headers=headers)
    assert task_response.status_code == 200
    task_payload = task_response.json()
    assert task_payload["status"] == "completed"
    assert task_payload["result_summary"] == "predicted:integration ml run"
    assert Decimal(task_payload["charged_tokens"]) == Decimal("18.00000000")

    balance_response = client.get("/balance/me", headers=headers)
    assert balance_response.status_code == 200
    assert Decimal(balance_response.json()["token_count"]) == Decimal("12.00000000")

    ledger_response = client.get("/balance/me/ledger", headers=headers)
    assert ledger_response.status_code == 200
    ledger_payload = ledger_response.json()
    assert [entry["kind"] for entry in ledger_payload] == ["debit", "credit"]
    assert Decimal(ledger_payload[0]["amount"]) == Decimal("18.00000000")
    assert ledger_payload[0]["task_id"] == task_id

    history_response = client.get("/history/me", headers=headers)
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert len(history_payload) == 1
    assert history_payload[0]["request"] == "integration ml run"
    assert history_payload[0]["result"] == "predicted:integration ml run"
    assert Decimal(history_payload[0]["tokens_charged"]) == Decimal("18.00000000")
    assert history_payload[0]["ml_task_id"] == task_id


def test_predict_rejects_invalid_payload_without_creating_side_effects(
    client,
    auth_headers,
    register_and_login,
) -> None:
    session = register_and_login(email="predict-invalid@example.com")
    headers = auth_headers(session.access_token)

    client.post("/balance/me/topup", headers=headers, json={"amount": "10.00"})

    invalid_response = client.post(
        "/predict",
        headers=headers,
        json={"model_id": "00000000-0000-4000-8000-000000000001", "text": ""},
    )
    assert invalid_response.status_code == 422
    assert invalid_response.json()["error"] == "request_validation_error"

    balance_response = client.get("/balance/me", headers=headers)
    assert Decimal(balance_response.json()["token_count"]) == Decimal("10.00")

    history_response = client.get("/history/me", headers=headers)
    assert history_response.status_code == 200
    assert history_response.json() == []

    ledger_response = client.get("/balance/me/ledger", headers=headers)
    assert len(ledger_response.json()) == 1
    assert ledger_response.json()[0]["kind"] == "credit"


def test_predict_rejects_insufficient_balance_without_side_effects(
    client,
    auth_headers,
    register_and_login,
) -> None:
    session = register_and_login(email="predict-insufficient@example.com")
    headers = auth_headers(session.access_token)

    predict_response = client.post(
        "/predict",
        headers=headers,
        json={"model_id": "00000000-0000-4000-8000-000000000001", "text": "need credits"},
    )
    assert predict_response.status_code == 409
    assert predict_response.json()["error"] == "insufficient_balance"

    balance_response = client.get("/balance/me", headers=headers)
    assert Decimal(balance_response.json()["token_count"]) == Decimal("0")

    history_response = client.get("/history/me", headers=headers)
    assert history_response.status_code == 200
    assert history_response.json() == []

    ledger_response = client.get("/balance/me/ledger", headers=headers)
    assert ledger_response.status_code == 200
    assert ledger_response.json() == []


def test_predict_internal_failure_keeps_balance_unchanged(
    client_factory,
    app,
    auth_headers,
    register_and_login,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with client_factory(raise_server_exceptions=False) as client:
        session = register_and_login(email="predict-error@example.com")
        headers = auth_headers(session.access_token)

        topup_response = client.post("/balance/me/topup", headers=headers, json={"amount": "25.00"})
        assert topup_response.status_code == 200

        monkeypatch.setattr(
            "app.modules.neural.service.toxicity_predict",
            lambda text, model_id: (_ for _ in ()).throw(RuntimeError("model exploded")),
        )

        predict_response = client.post(
            "/predict",
            headers=headers,
            json={"model_id": "00000000-0000-4000-8000-000000000001", "text": "will fail"},
        )
        assert predict_response.status_code == 500

        balance_response = client.get("/balance/me", headers=headers)
        assert balance_response.status_code == 200
        assert Decimal(balance_response.json()["token_count"]) == Decimal("25.00")

        history_response = client.get("/history/me", headers=headers)
        assert history_response.status_code == 200
        assert history_response.json() == []

        ledger_response = client.get("/balance/me/ledger", headers=headers)
        assert ledger_response.status_code == 200
        ledger_payload = ledger_response.json()
        assert len(ledger_payload) == 1
        assert ledger_payload[0]["kind"] == "credit"
