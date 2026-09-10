"""turns.duration_ms: latencia real por turno

La UI de metricas necesita cuanto tarda un turno. No se puede derivar de lo
que ya hay: las dos filas de ``chat_history`` de un turno (user y assistant)
se escriben en el MISMO commit, asi que su diferencia de ``created_at`` es
cero. El orquestador ahora mide el turno completo y lo persiste aca.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("turns", sa.Column("duration_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("turns", "duration_ms")
