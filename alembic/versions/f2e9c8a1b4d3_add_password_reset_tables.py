"""add_password_reset_tables

Revision ID: f2e9c8a1b4d3
Revises: 3a29b2f97391
Create Date: 2026-04-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2e9c8a1b4d3"
down_revision: Union[str, Sequence[str], None] = "3a29b2f97391"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("password_reset_attempts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_password_reset_attempts_email_normalized"),
            ["email_normalized"],
            unique=False,
        )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("password_reset_tokens", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_password_reset_tokens_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_password_reset_tokens_token_hash"), ["token_hash"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("password_reset_tokens", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_password_reset_tokens_token_hash"))
        batch_op.drop_index(batch_op.f("ix_password_reset_tokens_user_id"))

    op.drop_table("password_reset_tokens")

    with op.batch_alter_table("password_reset_attempts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_password_reset_attempts_email_normalized"))

    op.drop_table("password_reset_attempts")
