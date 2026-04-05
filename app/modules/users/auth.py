from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)
_token_to_user: dict[str, UUID] = {}
_pending_email_verifications: dict[str, tuple[UUID, str]] = {}
_verified_users: set[UUID] = set()


def issue_access_token(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    _token_to_user[token] = user_id
    return token


def resolve_access_token(token: str) -> UUID | None:
    return _token_to_user.get(token)


def issue_email_verification(user_id: UUID, email: str) -> str:
    normalized_email = email.strip().lower()
    code = secrets.token_hex(3).upper()
    _pending_email_verifications[normalized_email] = (user_id, code)
    _verified_users.discard(user_id)
    return code


def verify_email_code(email: str, code: str) -> UUID | None:
    normalized_email = email.strip().lower()
    pending = _pending_email_verifications.get(normalized_email)
    if pending is None:
        return None
    user_id, expected_code = pending
    if expected_code != code.strip().upper():
        return None
    _pending_email_verifications.pop(normalized_email, None)
    _verified_users.add(user_id)
    return user_id


def is_user_email_verified(user_id: UUID) -> bool:
    # Users not present in pending map are considered verified by default.
    if user_id in _verified_users:
        return True
    return all(pending_user_id != user_id for pending_user_id, _ in _pending_email_verifications.values())


def require_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
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

