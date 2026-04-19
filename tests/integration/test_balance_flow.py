from __future__ import annotations

from decimal import Decimal


def test_balance_topup_and_ledger_flow(client, auth_headers, auth_session_for_user, verified_user_factory) -> None:
    user = verified_user_factory(email="balance@example.com")
    session = auth_session_for_user(user)
    headers = auth_headers(session.access_token)

    initial_balance = client.get("/balance/me", headers=headers)
    assert initial_balance.status_code == 200
    assert Decimal(initial_balance.json()["token_count"]) == Decimal("0")

    topup_response = client.post("/balance/me/topup", headers=headers, json={"amount": "50.00"})
    assert topup_response.status_code == 200
    assert Decimal(topup_response.json()["token_count"]) == Decimal("50.00")

    updated_balance = client.get("/balance/me", headers=headers)
    assert updated_balance.status_code == 200
    assert Decimal(updated_balance.json()["token_count"]) == Decimal("50.00")

    ledger_response = client.get("/balance/me/ledger", headers=headers)
    assert ledger_response.status_code == 200
    ledger_payload = ledger_response.json()
    assert len(ledger_payload) == 1
    assert ledger_payload[0]["kind"] == "credit"
    assert Decimal(ledger_payload[0]["amount"]) == Decimal("50.00")
