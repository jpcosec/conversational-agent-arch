"""leads y visitas: info basica del lead y visitas solicitadas

Tablas planas que persisten las tools ``registrar_lead`` y ``crear_visita``
(negocios de venta con agendamiento, p.ej. Vitali). Ver
``kb_agent/models_sql/leads.py``.

Revision ID: f6a7b8c9d0e2
Revises: e5f6a7b8c9d1
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e2"
down_revision = "e5f6a7b8c9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("nombre", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("segmento", sa.String(), nullable=True),
        sa.Column("para_quien", sa.String(), nullable=True),
        sa.Column("edad_rango", sa.String(), nullable=True),
        sa.Column("ciudad", sa.String(), nullable=True),
        sa.Column("pais", sa.String(), nullable=True),
        sa.Column("proposito", sa.String(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "visitas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("lead_id", sa.Integer(), sa.ForeignKey("leads.id"), nullable=True),
        sa.Column("modalidad", sa.String(), nullable=False),
        sa.Column("preferencia", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=True),
        sa.Column("duracion_min", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("estado", sa.String(), nullable=False, server_default="solicitada"),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_visitas_user_id", "visitas", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_visitas_user_id", table_name="visitas")
    op.drop_table("visitas")
    op.drop_table("leads")
