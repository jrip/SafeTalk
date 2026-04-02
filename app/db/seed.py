from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.neural.models import MlModelModel

_ML_MODEL_SPECS: tuple[dict, ...] = (
    {
        "id": UUID("00000000-0000-4000-8000-000000000001"),
        "slug": "toxic-baseline",
        "name": "Toxicity baseline",
        "description": "Базовая модель токсичности для демо.",
        "version": "1.0.0",
        "is_active": True,
        "is_default": True,
        "price_per_character": Decimal("0.01"),
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000002"),
        "slug": "toxic-lite",
        "name": "Toxicity lite",
        "description": "Облегчённая модель (дешевле за запрос).",
        "version": "1.0.0",
        "is_active": True,
        "is_default": False,
        "price_per_character": Decimal("0.005"),
    },
)


def run_seed(session: Session) -> None:
    """Идемпотентно добавляет базовые ML-модели по уникальному slug."""
    for spec in _ML_MODEL_SPECS:
        slug = spec["slug"]
        if session.scalar(select(MlModelModel.id).where(MlModelModel.slug == slug)):
            continue
        session.add(MlModelModel(**spec))
    session.flush()
