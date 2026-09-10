"""inbound_messages: source de cada turno que entra por un canal externo

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-09-02 00:00:00.000000

Persiste cada mensaje que llega por un proveedor externo (Twilio WhatsApp/SMS)
con su id de proveedor, canal, payload crudo y el usuario/turno que origino.
UNIQUE(provider, provider_message_id) da idempotencia frente a los reintentos
del webhook de Twilio (antes un reintento creaba un segundo turno).
"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("to", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("profile_name", sa.String(), nullable=True),
        sa.Column("num_media", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("turn_id", sa.String(), nullable=True),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("reply_provider_message_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_message_id", name="uq_inbound_messages_provider_message_id"),
    )
    with op.batch_alter_table("inbound_messages", schema=None) as batch_op:
        batch_op.create_index("ix_inbound_messages_user_id_created_at", ["user_id", "created_at"], unique=False)
        batch_op.create_index("ix_inbound_messages_external_id", ["external_id"], unique=False)

    _backfill_users_phone()


def _canonical_phone(external_id: str) -> str | None:
    """Misma regla que ``Orchestrator._canonical_phone``: telefono canonico
    (``+`` + digitos) del id de un external_id con prefijo de canal; None si
    no hay prefijo (``ui:`` sin digitos, ``web-anon-...``) o no hay digitos."""
    _, sep, raw = external_id.partition(":")
    if not sep:
        return None
    compact = re.sub(r"[\s\-().]", "", raw)
    if not re.match(r"^\+?\d{7,15}$", compact):
        return None
    return "+" + compact.lstrip("+")


def _backfill_users_phone() -> None:
    """Rellena ``users.phone`` en filas creadas antes de ``identity_key='phone'``.

    Con ``identity_key='external_id'`` (default historico) ``ensure_user``
    dejaba ``phone`` NULL. Al pasar el proyecto a ``phone``, el usuario viejo
    ``whatsapp:+569X`` (phone NULL) no se unificaba con el nuevo
    ``sms:+569X``: quedaban dos personas. Se calcula el telefono canonico del
    external_id para las filas con prefijo de canal y digitos; ``ui:``/``web``
    sin digitos quedan NULL, como corresponde.
    """
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, external_id FROM users WHERE phone IS NULL")
    ).fetchall()
    for row_id, external_id in rows:
        phone = _canonical_phone(external_id or "")
        if phone:
            conn.execute(
                sa.text("UPDATE users SET phone = :phone WHERE id = :id"),
                {"phone": phone, "id": row_id},
            )


def downgrade() -> None:
    with op.batch_alter_table("inbound_messages", schema=None) as batch_op:
        batch_op.drop_index("ix_inbound_messages_external_id")
        batch_op.drop_index("ix_inbound_messages_user_id_created_at")
    op.drop_table("inbound_messages")
