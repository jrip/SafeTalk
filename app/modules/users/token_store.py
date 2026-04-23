from __future__ import annotations

import secrets
from uuid import UUID

_token_to_user: dict[str, UUID] = {}


def issue_access_token(user_id: UUID) -> str:
    token = secrets.token_urlsafe(32)
    _token_to_user[token] = user_id
    return token


def resolve_access_token(token: str) -> UUID | None:
    return _token_to_user.get(token)


def revoke_access_tokens_for_user(user_id: UUID) -> None:
    """Invalidate all bearer tokens issued for the user."""
    to_remove = [token for token, token_user_id in _token_to_user.items() if token_user_id == user_id]
    for token in to_remove:
        del _token_to_user[token]
