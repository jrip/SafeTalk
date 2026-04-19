"""seed_ml_models

Revision ID: 3a29b2f97391
Revises: 7b57ba2d1df5
Create Date: 2026-04-19 21:18:08.295621

"""
from decimal import Decimal
from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a29b2f97391'
down_revision: Union[str, Sequence[str], None] = '7b57ba2d1df5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ml_models_table = sa.table(
    "ml_models",
    sa.column("id", sa.Uuid()),
    sa.column("slug", sa.String(length=64)),
    sa.column("name", sa.String(length=255)),
    sa.column("description", sa.Text()),
    sa.column("version", sa.String(length=64)),
    sa.column("is_active", sa.Boolean()),
    sa.column("is_default", sa.Boolean()),
    sa.column("price_per_character", sa.Numeric(24, 8)),
)

MODEL_ROWS = [
    {
        "id": UUID("00000000-0000-4000-8000-000000000001"),
        "slug": "toxic-baseline",
        "name": "Базовая модель токсичности",
        "description": "Multilabel токсичность",
        "version": "1.0.0",
        "is_active": True,
        "is_default": True,
        "price_per_character": Decimal("1.00"),
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000002"),
        "slug": "toxic-lite",
        "name": "Облегченная модель",
        "description": "Облегчённая модель",
        "version": "1.0.0",
        "is_active": True,
        "is_default": False,
        "price_per_character": Decimal("0.50"),
    },
]


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(ml_models_table, MODEL_ROWS)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text("DELETE FROM ml_models WHERE id IN (:id1, :id2)").bindparams(
            id1=str(MODEL_ROWS[0]["id"]),
            id2=str(MODEL_ROWS[1]["id"]),
        )
    )
