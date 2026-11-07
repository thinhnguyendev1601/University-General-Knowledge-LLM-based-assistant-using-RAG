"""Accounts, conversations and document lifecycle metadata."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin')", name="ck_users_role"),
        CheckConstraint("status IN ('pending', 'active', 'disabled')", name="ck_users_status"),
        CheckConstraint("email = lower(email) AND email LIKE '%@university.edu.vn'", name="ck_users_email"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    status: Mapped[str] = mapped_column(String(16), default="active")
    # Historical verification metadata; new registrations do not verify email ownership.
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('verify', 'reset')", name="ck_account_tokens_purpose"),
        Index("ix_account_tokens_user_purpose", "user_id", "purpose"),
        Index("ix_account_tokens_expires", "expires_at"),
        Index("ix_account_tokens_consumed", "consumed_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class LoginSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_expires", "expires_at"),
                      Index("ix_sessions_seen", "last_seen_at"), Index("ix_sessions_revoked", "revoked_at"))
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # SHA-256 of a random cookie
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RateLimit(Base):
    __tablename__ = "rate_limits"
    __table_args__ = (Index("ix_rate_limits_window", "window_start"),)
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    window_start: Mapped[int] = mapped_column(Integer)
    count: Mapped[int] = mapped_column(Integer)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_owner_updated", "user_id", "updated_at", "id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    active_request_id: Mapped[str | None] = mapped_column(String(36))
    generation_token: Mapped[str | None] = mapped_column(String(36))
    generation_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint("delivery_state IN ('pending', 'completed', 'failed')", name="ck_messages_delivery_state"),
        Index("uq_messages_sequence", "conversation_id", "sequence", unique=True),
        Index("uq_messages_request_role", "conversation_id", "request_id", "role", unique=True),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    citations: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sequence: Mapped[int] = mapped_column(Integer)
    request_id: Mapped[str | None] = mapped_column(String(36))
    delivery_state: Mapped[str] = mapped_column(String(16), default="completed", server_default="completed")
    details: Mapped[dict | None] = mapped_column(JSON)


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("corpus_role IN ('indexed', 'holdout', 'excluded')", name="ck_documents_corpus_role"),
        CheckConstraint("doc_status IN ('current', 'superseded', 'unknown')", name="ck_documents_status"),
        CheckConstraint("lang IN ('vi', 'en', 'mixed')", name="ck_documents_lang"),
        Index("ix_documents_created", "created_at", "id"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    # Stable legacy identifier: chunk IDs remain <doc_id>:<start>:<end>.
    legacy_doc_id: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(1000))
    publisher: Mapped[str] = mapped_column(String(500))
    institution_id: Mapped[str | None] = mapped_column(String(64), index=True)
    doc_type: Mapped[str] = mapped_column(String(64))
    lang: Mapped[str] = mapped_column(String(8))
    corpus_role: Mapped[str] = mapped_column(String(16))
    doc_status: Mapped[str] = mapped_column(String(16))
    source_url: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[str | None] = mapped_column(String(64))
    effective_date: Mapped[str | None] = mapped_column(String(64))
    version_group: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("uq_document_versions_label", "document_id", "version_label", unique=True),
        CheckConstraint("origin IN ('manifest', 'upload')", name="ck_document_versions_origin"),
        CheckConstraint("processing_status IN ('uploaded', 'processing', 'ready', 'failed')",
                        name="ck_document_versions_processing"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="RESTRICT"), index=True)
    version_label: Mapped[str] = mapped_column(String(128))
    origin: Mapped[str] = mapped_column(String(16))
    # NULL for legacy metadata: importing a row does not prove ingestion/publication.
    processing_status: Mapped[str | None] = mapped_column(String(16))
    file_format: Mapped[str | None] = mapped_column(String(16))
    sha256_raw: Mapped[str | None] = mapped_column(String(64))
    sha256_text: Mapped[str | None] = mapped_column(String(64))
    n_pages: Mapped[int | None] = mapped_column(Integer)
    manifest_metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentAudit(Base):
    __tablename__ = "document_audit"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="RESTRICT"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_kind: Mapped[str] = mapped_column(String(32))  # admin or manifest_import
    action: Mapped[str] = mapped_column(String(64))
    changes: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
