from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.users.token_store import (
    _token_to_user,
    issue_access_token,
    revoke_access_tokens_for_user,
    resolve_access_token,
)

# Security (а не Depends) — чтобы в OpenAPI появилась схема и в Swagger была кнопка Authorize.
_bearer = HTTPBearer(
    auto_error=False,
    description="Токен из ответа POST /auth/login. В поле вставь только сам токен (префикс Bearer Swagger добавит).",
)


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

