from __future__ import annotations

def test_register_verify_login_and_get_profile_flow(client, auth_headers) -> None:
    register_response = client.post(
        "/auth/register",
        json={"login": "flow@example.com", "password": "StrongPass123", "name": "Flow User"},
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()

    verify_response = client.post(
        "/auth/verify-email",
        json={"login": "flow@example.com", "code": register_payload["temporary_only_for_test_todo"]},
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/auth/login",
        json={"login": "flow@example.com", "password": "StrongPass123"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = client.get("/users/me", headers=auth_headers(access_token))
    assert me_response.status_code == 200
    me_payload = me_response.json()

    assert me_payload["id"] == register_payload["id"]
    assert me_payload["name"] == "Flow User"
    assert me_payload["identities"] == ["email:flow@example.com"]


def test_health_endpoint_returns_ok(client) -> None:
    health_response = client.get("/health")
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}


def test_db_health_endpoint_returns_connected(client) -> None:
    db_health_response = client.get("/health/db")
    assert db_health_response.status_code == 200
    assert db_health_response.json() == {"status": "ok", "database": "connected"}


def test_login_rejects_unverified_user(client, unverified_user_factory) -> None:
    unverified_user = unverified_user_factory(email="auth-unverified@example.com", name="Auth Errors")
    unverified_login = client.post(
        "/auth/login",
        json={"login": unverified_user.email, "password": unverified_user.password},
    )
    assert unverified_login.status_code == 400
    assert unverified_login.json()["message"] == "Email is not verified"


def test_login_rejects_wrong_password(client, verified_user_factory) -> None:
    verified_user = verified_user_factory(email="auth-wrong-password@example.com", name="Auth Errors")
    wrong_password = client.post(
        "/auth/login",
        json={"login": verified_user.email, "password": "WrongPass123"},
    )
    assert wrong_password.status_code == 400
    assert wrong_password.json()["message"] == "Нет такого пользователя или неверный пароль"


def test_login_rejects_missing_user(client) -> None:
    missing_user = client.post(
        "/auth/login",
        json={"login": "missing-user@example.com", "password": "WrongPass123"},
    )
    assert missing_user.status_code == 400
    assert missing_user.json()["message"] == "Нет такого пользователя или неверный пароль"


def test_protected_route_rejects_missing_bearer_token(client) -> None:
    missing_token = client.get("/balance/me")
    assert missing_token.status_code == 401
    assert missing_token.json()["message"] == "Missing or invalid bearer token"


def test_protected_route_rejects_invalid_access_token(client) -> None:
    invalid_token = client.get("/history/me", headers={"Authorization": "Bearer deadbeef"})
    assert invalid_token.status_code == 401
    assert invalid_token.json()["message"] == "Invalid access token"
