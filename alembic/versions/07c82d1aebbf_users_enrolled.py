"""users.enrolled

Revision ID: 07c82d1aebbf
Revises: 8df38d93ccd7
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '07c82d1aebbf'
down_revision: Union[str, Sequence[str], None] = '8df38d93ccd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Server default False: cualquier fila nueva que no fije el valor
    # explicitamente (inserts crudos, fixtures) arranca como NO inscrita,
    # que es la opcion segura -- exige pasar por el enrolamiento antes de
    # tratarla como paciente conocida.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enrolled', sa.Boolean(), nullable=False, server_default=sa.false()))

    # Backfill de filas existentes: los usuarios sembrados desde el feed del
    # PSP (external_id wa-* de WhatsApp, web-anon-* del canal web) ya vienen
    # inscritos por el laboratorio -- no pasaron ni deben pasar por el step
    # de enrolamiento. Cualquier otro external_id (p.ej. ui:* de la UI de
    # chat de desarrollo) no tiene esa garantia y queda en False, que ya es
    # el valor que puso el server_default de arriba.
    op.execute(
        "UPDATE users SET enrolled = 1 "
        "WHERE external_id LIKE 'wa-%' OR external_id LIKE 'web-anon-%'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('enrolled')
