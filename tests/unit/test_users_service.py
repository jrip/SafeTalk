from __future__ import annotations

import pytest

from app.core import ValidationError
from app.modules.users.types import AuthInput, CreateUserInput


def test_user_must_verify_email_before_login(app_container) -> None:
    user = app_container.users.register(CreateUserInput(name="Alice"))
    app_container.users.register_email_identity(user.id, "alice@example.com", "Secret123")

    with pytest.raises(ValidationError, match="Email is not verified"):
        app_container.users.get_auth_token(
            AuthInput(
                identity_type="email",
                identifier="alice@example.com",
                password_hash="Secret123",
            )
        )

    verification_code = app_container.users.start_email_verification("alice@example.com")
    app_container.users.verify_email_code("alice@example.com", verification_code)

    token = app_container.users.get_auth_token(
        AuthInput(
            identity_type="email",
            identifier="alice@example.com",
            password_hash="Secret123",
        )
    )

    assert token.access_token == str(user.id)
    identity = app_container.users.get_email_identity("alice@example.com")
    assert identity is not None
    assert identity.is_verified is True


def test_register_email_identity_rejects_duplicate_login(app_container) -> None:
    first_user = app_container.users.register(CreateUserInput(name="First"))
    app_container.users.register_email_identity(first_user.id, "shared@example.com", "Secret123")

    second_user = app_container.users.register(CreateUserInput(name="Second"))

    with pytest.raises(ValidationError, match="Login already registered"):
        app_container.users.register_email_identity(second_user.id, "shared@example.com", "Another123")


def test_verify_email_code_decrements_attempts_on_invalid_code(app_container) -> None:
    user = app_container.users.register(CreateUserInput(name="Retry User"))
    app_container.users.register_email_identity(user.id, "retry@example.com", "Secret123")
    app_container.users.start_email_verification("retry@example.com")

    with pytest.raises(ValidationError, match=r"Attempts left: 2"):
        app_container.users.verify_email_code("retry@example.com", "WRONG1")

    identity = app_container.users.get_email_identity("retry@example.com")
    assert identity is not None
    assert identity.verification_attempts_left == 2
