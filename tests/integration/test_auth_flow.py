from __future__ import annotations

from decimal import Decimal


def test_register_verify_login_and_get_profile_flow(client, auth_headers, register_and_login) -> None:
    session = register_and_login(email="flow@example.com", name="Flow User")

    me_response = client.get("/users/me", headers=auth_headers(session.access_token))
    assert me_response.status_code == 200
    me_payload = me_response.json()

    assert me_payload["id"] == session.user_id
    assert me_payload["name"] == "Flow User"
    assert me_payload["identities"] == ["email:flow@example.com"]

    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}

    db_health_response = client.get("/health/db")
    assert db_health_response.status_code == 200
    assert db_health_response.json() == {"status": "ok", "database": "connected"}


def test_login_rejects_unverified_user_and_wrong_password(client) -> None:
    register_response = client.post(
        "/auth/register",
        json={"login": "auth-errors@example.com", "password": "StrongPass123", "name": "Auth Errors"},
    )
    assert register_response.status_code == 201

    unverified_login = client.post(
        "/auth/login",
        json={"login": "auth-errors@example.com", "password": "StrongPass123"},
    )
    assert unverified_login.status_code == 400
    assert unverified_login.json()["message"] == "Email is not verified"

    verification_code = register_response.json()["temporary_only_for_test_todo"]
    verify_response = client.post(
        "/auth/verify-email",
        json={"login": "auth-errors@example.com", "code": verification_code},
    )
    assert verify_response.status_code == 200

    wrong_password = client.post(
        "/auth/login",
        json={"login": "auth-errors@example.com", "password": "WrongPass123"},
    )
    assert wrong_password.status_code == 400
    assert wrong_password.json()["message"] == "Invalid credentials"


def test_protected_routes_require_valid_bearer_token(client) -> None:
    missing_token = client.get("/balance/me")
    assert missing_token.status_code == 401
    assert missing_token.json()["message"] == "Missing or invalid bearer token"

    invalid_token = client.get("/history/me", headers={"Authorization": "Bearer deadbeef"})
    assert invalid_token.status_code == 401
    assert invalid_token.json()["message"] == "Invalid access token"
