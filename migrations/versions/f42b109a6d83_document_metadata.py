"""Add document metadata, immutable imported versions and admin audit."""
from alembic import op
import sqlalchemy as sa

revision = "f42b109a6d83"
down_revision = "e3f90124a8c7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("legacy_doc_id", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("publisher", sa.String(500), nullable=False),
        sa.Column("institution_id", sa.String(64)),
        sa.Column("doc_type", sa.String(64), nullable=False),
        sa.Column("lang", sa.String(8), nullable=False),
        sa.Column("corpus_role", sa.String(16), nullable=False),
        sa.Column("doc_status", sa.String(16), nullable=False),
        sa.Column("source_url", sa.Text()),
        sa.Column("publication_date", sa.String(64)),
        sa.Column("effective_date", sa.String(64)),
        sa.Column("version_group", sa.String(200)),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("corpus_role IN ('indexed', 'holdout', 'excluded')", name="ck_documents_corpus_role"),
        sa.CheckConstraint("doc_status IN ('current', 'superseded', 'unknown')", name="ck_documents_status"),
        sa.CheckConstraint("lang IN ('vi', 'en', 'mixed')", name="ck_documents_lang"),
    )
    op.create_index("ix_documents_created", "documents", ["created_at", "id"])
    op.create_index("ix_documents_institution_id", "documents", ["institution_id"])
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version_label", sa.String(128), nullable=False),
        sa.Column("origin", sa.String(16), nullable=False),
        sa.Column("processing_status", sa.String(16)),
        sa.Column("file_format", sa.String(16)),
        sa.Column("sha256_raw", sa.String(64)),
        sa.Column("sha256_text", sa.String(64)),
        sa.Column("n_pages", sa.Integer()),
        sa.Column("manifest_metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origin IN ('manifest', 'upload')", name="ck_document_versions_origin"),
        sa.CheckConstraint("processing_status IN ('uploaded', 'processing', 'ready', 'failed')",
                           name="ck_document_versions_processing"),
    )
    op.create_index("ix_document_versions_document_id", "document_versions", ["document_id"])
    op.create_index("uq_document_versions_label", "document_versions", ["document_id", "version_label"], unique=True)
    op.create_table(
        "document_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("actor_kind", sa.String(32), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_document_audit_document_id", "document_audit", ["document_id"])


def downgrade():
    op.drop_table("document_audit")
    op.drop_table("document_versions")
    op.drop_table("documents")
