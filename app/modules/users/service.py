from __future__ import annotations

from uuid import UUID

from app.core import ValidationError
from app.modules.users.interfaces import UsersInternalService
from app.modules.users.types import AuthInput, AuthTokenView, CreateUserInput, UpdateUserInput, UserView


class UserService(UsersInternalService):
    def __init__(self) -> None:
        """Сервис Users без реализации хранения (на этапе проектирования)."""

    def register(self, payload: CreateUserInput) -> UserView:
        """Внешний метод: регистрация пользователя."""
        raise NotImplementedError("Storage/auth is mocked at this stage")

    def get_auth_token(self, payload: AuthInput) -> AuthTokenView:
        """Внешний метод: получение токена авторизации."""
        raise NotImplementedError("Auth is mocked at this stage")

    def get_profile(self, user_id: UUID) -> UserView:
        """Внешний метод: получить информацию о текущем пользователе."""
        raise NotImplementedError("Profile lookup is mocked at this stage")

    def update_profile(self, user_id: UUID, payload: UpdateUserInput) -> UserView:
        """Внешний метод: обновить информацию о текущем пользователе."""
        raise NotImplementedError("Profile update is mocked at this stage")

    @staticmethod
    def normalize_name(name: str) -> str:
        """Сервисная валидация/нормализация имени пользователя."""
        normalized = name.strip()
        if not normalized:
            raise ValidationError("User name cannot be empty")
        return normalized

    @staticmethod
    def is_password_match(stored_hash: str, incoming_hash: str) -> bool:
        """Сервисная проверка совпадения хеша пароля."""
        return stored_hash == incoming_hash

