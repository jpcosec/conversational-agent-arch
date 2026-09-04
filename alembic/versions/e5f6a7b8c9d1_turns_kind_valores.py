"""turns.kind: normalizar a los VALORES del enum (agent/user/override)

La migracion c1a2b3d4e5f6 creo la columna con ``server_default="agent"`` (el
VALOR del enum) mientras el modelo la leia por NOMBRE ("AGENT"). Resultado
medido en la base de produccion de Vitali: toda fila anterior a esa
migracion quedo con "agent" y el ORM no podia leerla --
``LookupError: 'agent' is not among the defined enum values`` -- rompiendo
/api/history (Turn Inspector de conversaciones pasadas) y /api/metrics.

El modelo pasa a persistir valores (``values_callable``); aca se normalizan
las filas que quedaron con el nombre en mayusculas.

Revision ID: e5f6a7b8c9d1
Revises: e5f6a7b8c9d0
"""
from __future__ import annotations

from alembic import op

revision = "e5f6a7b8c9d1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 'AGENT' -> 'agent', 'USER' -> 'user', 'OVERRIDE' -> 'override'.
    op.execute("UPDATE turns SET kind = lower(kind) WHERE kind <> lower(kind)")


def downgrade() -> None:
    op.execute("UPDATE turns SET kind = upper(kind) WHERE kind <> upper(kind)")
