"""recontactos y consentimientos: tools del piloto HCP

Tablas planas que persisten las tools ``programar_recontacto`` y
``actualizar_consentimiento`` (KB ``knowledge_hcp``). Ver
``kb_agent/models_sql/hcp.py``.

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
        "recontactos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("fecha_recontacto", sa.String(), nullable=False),
        sa.Column("franja_horaria", sa.String(), nullable=True),
        sa.Column("campania_id", sa.String(), nullable=True),
        sa.Column("nota_contexto", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "consentimientos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("nuevo_estado", sa.String(), nullable=False),
        sa.Column("campania_id", sa.String(), nullable=True),
        sa.Column("motivo_verbatim", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("consentimientos")
    op.drop_table("recontactos")
