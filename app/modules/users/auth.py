from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.settings import get_settings

_bearer = HTTPBearer(auto_error=False)
_token_to_user: dict[str, UUID] = {}
@dataclass
class PendingEmailVerification:
    user_id: UUID
    code: str
    expires_at: datetime
    attempts_left: int


_pending_email_verifications: dict[str, PendingEmailVerification] = {}
_verified_users: set[UUID] = set()


def issue_access_token(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    _token_to_user[token] = user_id
    return token


def resolve_access_token(token: str) -> UUID | None:
    return _token_to_user.get(token)


def issue_email_verification(user_id: UUID, login: str) -> str:
    settings = get_settings()
    normalized_login = login.strip().lower()
    code = secrets.token_hex(3).upper()
    _pending_email_verifications[normalized_login] = PendingEmailVerification(
        user_id=user_id,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.email_verification_ttl_seconds),
        attempts_left=settings.email_verification_max_attempts,
    )
    _verified_users.discard(user_id)
    return code


def verify_email_code(login: str, code: str) -> UUID | None:
    normalized_login = login.strip().lower()
    pending = _pending_email_verifications.get(normalized_login)
    if pending is None:
        return None

    if datetime.now(timezone.utc) > pending.expires_at:
        _pending_email_verifications.pop(normalized_login, None)
        return None

    submitted = code.strip().upper()
    if pending.code != submitted:
        pending.attempts_left -= 1
        if pending.attempts_left <= 0:
            _pending_email_verifications.pop(normalized_login, None)
        else:
            _pending_email_verifications[normalized_login] = pending
        return None

    _pending_email_verifications.pop(normalized_login, None)
    _verified_users.add(pending.user_id)
    return pending.user_id


def get_email_verification_status(login: str) -> dict[str, int]:
    normalized_login = login.strip().lower()
    pending = _pending_email_verifications.get(normalized_login)
    if pending is None:
        return {"attempts_left": 0, "expires_in_seconds": 0}
    expires_in = max(0, int((pending.expires_at - datetime.now(timezone.utc)).total_seconds()))
    return {"attempts_left": pending.attempts_left, "expires_in_seconds": expires_in}


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

