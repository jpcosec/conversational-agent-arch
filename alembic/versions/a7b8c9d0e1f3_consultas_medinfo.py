"""consultas: tickets MedInfo y reportes de evento adverso (tool registrar_consulta)

Ver ``kb_agent/models_sql/consultas.py``.

Revision ID: a7b8c9d0e1f3
Revises: f6a7b8c9d0e2
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a7b8c9d0e1f3"
down_revision = "f6a7b8c9d0e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("urgente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("estado", sa.String(), nullable=False, server_default="abierta"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("consultas")
