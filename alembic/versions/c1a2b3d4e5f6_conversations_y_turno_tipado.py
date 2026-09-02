"""conversations (entidad) + conversation_id/kind en turns y chat_history

Revision ID: c1a2b3d4e5f6
Revises: 07c82d1aebbf
Create Date: 2026-08-31 00:00:00.000000

Modela la entidad Conversation (decision del owner): un usuario tiene una lista
de conversaciones; una conversacion es una lista de turnos acotada en el tiempo.
Tipa el turno (user/agent/override) y liga turns + chat_history a su
conversacion, para que el historial que va al prompt no cruce el limite de la
conversacion. Columnas nuevas nullable => compatible con filas existentes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "07c82d1aebbf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.create_index("ix_conversations_user_id_status", ["user_id", "status"], unique=False)
        batch_op.create_index("ix_conversations_user_id_last_activity", ["user_id", "last_activity_at"], unique=False)

    with op.batch_alter_table("turns", schema=None) as batch_op:
        batch_op.add_column(sa.Column("conversation_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("kind", sa.String(), nullable=False, server_default="agent"))
        batch_op.create_foreign_key("fk_turns_conversation_id", "conversations", ["conversation_id"], ["id"])
        batch_op.create_index("ix_turns_conversation_id_created_at", ["conversation_id", "created_at"], unique=False)

    with op.batch_alter_table("chat_history", schema=None) as batch_op:
        batch_op.add_column(sa.Column("conversation_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_chat_history_conversation_id", "conversations", ["conversation_id"], ["id"])
        batch_op.create_index("ix_chat_history_conversation_id_created_at", ["conversation_id", "created_at"], unique=False)

    # Identidad canonica por telefono (identity_key='phone'): unifica al mismo
    # usuario entre canales. Nullable => compatible con filas/canales sin tel.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(), nullable=True))
        batch_op.create_index("ix_users_phone", ["phone"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_phone")
        batch_op.drop_column("phone")

    with op.batch_alter_table("chat_history", schema=None) as batch_op:
        batch_op.drop_index("ix_chat_history_conversation_id_created_at")
        batch_op.drop_constraint("fk_chat_history_conversation_id", type_="foreignkey")
        batch_op.drop_column("conversation_id")

    with op.batch_alter_table("turns", schema=None) as batch_op:
        batch_op.drop_index("ix_turns_conversation_id_created_at")
        batch_op.drop_constraint("fk_turns_conversation_id", type_="foreignkey")
        batch_op.drop_column("kind")
        batch_op.drop_column("conversation_id")

    with op.batch_alter_table("conversations", schema=None) as batch_op:
        batch_op.drop_index("ix_conversations_user_id_last_activity")
        batch_op.drop_index("ix_conversations_user_id_status")
    op.drop_table("conversations")
