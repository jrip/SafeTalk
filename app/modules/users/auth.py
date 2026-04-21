from __future__ import annotations

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Security (а не Depends) — чтобы в OpenAPI появилась схема и в Swagger была кнопка Authorize.
_bearer = HTTPBearer(
    auto_error=False,
    description="Токен из ответа POST /auth/login. В поле вставь только сам токен (префикс Bearer Swagger добавит).",
)
_token_to_user: dict[str, UUID] = {}


def issue_access_token(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    _token_to_user[token] = user_id
    return token


def resolve_access_token(token: str) -> UUID | None:
    return _token_to_user.get(token)


def revoke_access_tokens_for_user(user_id: UUID) -> None:
    """Инвалидирует все bearer-токены, выданные для user_id (например после смены пароля)."""
    to_remove = [t for t, uid in _token_to_user.items() if uid == user_id]
    for t in to_remove:
        del _token_to_user[t]


def require_user_id(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer),
    ],
) -> UUID:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = resolve_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id

