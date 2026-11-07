"""Activate existing pending accounts under the domain-only signup policy."""
from alembic import op

revision = "d72a08b1ee51"
down_revision = "c941e3743994"
branch_labels = None
depends_on = None


def upgrade():
    # Pending accounts were already validated against the exact university domain.
    # Do not reactivate disabled users or claim that any mailbox was verified.
    op.execute("UPDATE users SET status = 'active' WHERE status = 'pending'")
    op.execute("UPDATE account_tokens SET consumed_at = CURRENT_TIMESTAMP "
               "WHERE purpose = 'verify' AND consumed_at IS NULL")


def downgrade():
    # Activation cannot be reversed safely: active accounts may now be in use.
    pass
