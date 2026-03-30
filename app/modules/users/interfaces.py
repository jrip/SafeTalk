from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.modules.users.types import AuthInput, AuthTokenView, CreateUserInput, UpdateUserInput, UserView


class UsersPublicService(Protocol):
    def register(self, payload: CreateUserInput) -> UserView:
        """Внешний метод: регистрация пользователя."""

    def get_auth_token(self, payload: AuthInput) -> AuthTokenView:
        """Внешний метод: получение токена авторизации."""

    def get_profile(self, user_id: UUID) -> UserView:
        """Внешний метод: получить информацию о текущем пользователе."""

    def update_profile(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        """Внешний метод: обновить информацию о текущем пользователе."""


class UsersInternalService(UsersPublicService, Protocol):
    """Внутренний интерфейс Users включает весь внешний контракт."""
