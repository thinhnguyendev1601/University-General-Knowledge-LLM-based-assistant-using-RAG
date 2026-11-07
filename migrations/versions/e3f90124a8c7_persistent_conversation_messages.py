"""Persist ordered chat turns and generation/retry metadata."""
from alembic import op
import sqlalchemy as sa

revision = "e3f90124a8c7"
down_revision = "d72a08b1ee51"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversations", sa.Column("active_request_id", sa.String(36), nullable=True))
    op.add_column("conversations", sa.Column("generation_token", sa.String(36), nullable=True))
    op.add_column("conversations", sa.Column("generation_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_conversations_owner_updated", "conversations", ["user_id", "updated_at", "id"])
    op.add_column("messages", sa.Column("sequence", sa.Integer(), nullable=True))
    op.add_column("messages", sa.Column("request_id", sa.String(36), nullable=True))
    op.add_column("messages", sa.Column("delivery_state", sa.String(16), server_default="completed", nullable=False))
    op.add_column("messages", sa.Column("details", sa.JSON(), nullable=True))
    # Preserve any existing messages, with deterministic order inside each conversation.
    op.execute("""WITH numbered AS (
        SELECT id, ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY created_at, id) AS position
        FROM messages
    ) UPDATE messages SET sequence = (SELECT position FROM numbered WHERE numbered.id = messages.id)""")
    with op.batch_alter_table("messages") as batch:
        batch.alter_column("sequence", existing_type=sa.Integer(), nullable=False)
        batch.create_check_constraint("ck_messages_delivery_state", "delivery_state IN ('pending', 'completed', 'failed')")
        batch.create_index("uq_messages_sequence", ["conversation_id", "sequence"], unique=True)
        batch.create_index("uq_messages_request_role", ["conversation_id", "request_id", "role"], unique=True)


def downgrade():
    with op.batch_alter_table("messages") as batch:
        batch.drop_index("uq_messages_request_role")
        batch.drop_index("uq_messages_sequence")
        batch.drop_constraint("ck_messages_delivery_state", type_="check")
        batch.drop_column("details")
        batch.drop_column("delivery_state")
        batch.drop_column("request_id")
        batch.drop_column("sequence")
    op.drop_index("ix_conversations_owner_updated", table_name="conversations")
    op.drop_column("conversations", "generation_started_at")
    op.drop_column("conversations", "generation_token")
    op.drop_column("conversations", "active_request_id")
