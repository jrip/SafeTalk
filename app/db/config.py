from __future__ import annotations

"""Базовый класс ORM и импорт модулей моделей в metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс ORM."""


import app.modules.users.models  # noqa: F401, E402 — регистрация в Base.metadata
import app.modules.billing.models  # noqa: F401, E402
import app.modules.neural.models  # noqa: F401, E402
import app.modules.history.models  # noqa: F401, E402
import app.modules.feedback.models  # noqa: F401, E402
