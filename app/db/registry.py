"""Импорт ORM-модулей для регистрации таблиц в Base.metadata."""

from __future__ import annotations

import app.modules.users.models  # noqa: F401
import app.modules.billing.models  # noqa: F401
import app.modules.neural.models  # noqa: F401
import app.modules.history.models  # noqa: F401
import app.modules.feedback.models  # noqa: F401
