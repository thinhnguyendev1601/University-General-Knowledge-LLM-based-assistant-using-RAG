"""Indexes for bounded operational cleanup; no content is removed by migration."""
from alembic import op

revision = "a76d18b4c902"
down_revision = "f42b109a6d83"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_account_tokens_expires", "account_tokens", "expires_at"),
    ("ix_account_tokens_consumed", "account_tokens", "consumed_at"),
    ("ix_sessions_expires", "sessions", "expires_at"),
    ("ix_sessions_seen", "sessions", "last_seen_at"),
    ("ix_sessions_revoked", "sessions", "revoked_at"),
    ("ix_rate_limits_window", "rate_limits", "window_start"),
)


def upgrade():
    for name, table, column in INDEXES:
        op.create_index(name, table, [column])


def downgrade():
    for name, table, column in reversed(INDEXES):
        op.drop_index(name, table_name=table)
