from __future__ import annotations

from uuid import UUID

from app.modules.users.interfaces import UsersPublicService
from app.modules.users.types import AuthInput, AuthTokenView, CreateUserInput, UpdateUserInput, UserView


class UsersController:
    """HTTP-контроллер внешнего API модуля Users."""

    def __init__(self, service: UsersPublicService) -> None:
        self._service = service

    def register(self, payload: CreateUserInput) -> UserView:
        """Регистрация пользователя."""
        return self._service.register(payload)

    def get_token(self, payload: AuthInput) -> AuthTokenView:
        """Получение токена авторизации."""
        return self._service.get_auth_token(payload)

    def get_me(self, user_id: UUID) -> UserView:
        """Получение информации о текущем пользователе."""
        return self._service.get_profile(user_id)

    def update_me(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        """Обновление информации о текущем пользователе."""
        return self._service.update_profile(user_id, payload)
