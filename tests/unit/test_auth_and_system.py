from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.modules.system.routes import health, health_db
from app.modules.users.auth import (
    issue_access_token,
    require_user_id,
    resolve_access_token,
    revoke_access_tokens_for_user,
)


def test_issue_and_resolve_access_token_roundtrip() -> None:
    user_id = uuid4()

    token = issue_access_token(user_id)

    assert isinstance(token, str)
    assert resolve_access_token(token) == user_id
    assert require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)) == user_id


def test_require_user_id_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_user_id(None)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid bearer token"


def test_require_user_id_rejects_wrong_scheme() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_user_id(HTTPAuthorizationCredentials(scheme="Basic", credentials="abc"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Missing or invalid bearer token"


def test_require_user_id_rejects_unknown_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_user_id(HTTPAuthorizationCredentials(scheme="Bearer", credentials="unknown-token"))

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid access token"


def test_revoke_access_tokens_for_user_invalidates_tokens() -> None:
    user_id = uuid4()
    t1 = issue_access_token(user_id)
    t2 = issue_access_token(user_id)
    assert resolve_access_token(t1) == user_id
    assert resolve_access_token(t2) == user_id

    revoke_access_tokens_for_user(user_id)

    assert resolve_access_token(t1) is None
    assert resolve_access_token(t2) is None


def test_system_health_route_returns_ok() -> None:
    assert health() == {"status": "ok"}


def test_system_db_health_route_returns_connected(session) -> None:
    assert health_db(session) == {"status": "ok", "database": "connected"}
