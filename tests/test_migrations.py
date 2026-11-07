from alembic import command
from alembic.config import Config
from contextlib import closing
from datetime import timedelta
import json
import os
import uuid
import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from api.settings import ROOT, get_settings
from api.models import AccountToken, Document, DocumentVersion, Message, User, utcnow
from scripts.import_document_metadata import import_manifest
from scripts.seed_demo_accounts import seed_demo_accounts


def test_initial_migration_upgrade_downgrade_and_model_alignment(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(ROOT / "alembic.ini"))
    try:
        command.upgrade(config, "head")
        engine = create_engine(url)
        assert {"users", "sessions", "account_tokens", "rate_limits", "conversations", "messages"} <= set(inspect(engine).get_table_names())
        command.check(config)
        engine.dispose()
        command.downgrade(config, "base")
        engine = create_engine(url)
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
        engine.dispose()
        command.upgrade(config, "head")
    finally:
        get_settings.cache_clear()


def test_domain_only_migration_activates_pending_but_not_disabled_accounts(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'existing_accounts.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_engine(url)
    try:
        command.upgrade(config, "c941e3743994")
        with Session(engine) as db:
            pending = User(email="pending@university.edu.vn", name="Pending", password_hash="old-hash", status="pending")
            disabled = User(email="disabled@university.edu.vn", name="Disabled", password_hash="old-hash", status="disabled")
            db.add_all([pending, disabled])
            db.flush()
            db.add(AccountToken(user_id=pending.id, token_hash="a" * 64, purpose="verify",
                                expires_at=utcnow() + timedelta(minutes=30)))
            db.commit()
        command.upgrade(config, "head")
        with Session(engine) as db:
            users = {user.email: user for user in db.scalars(select(User))}
            assert users["pending@university.edu.vn"].status == "active"
            assert users["pending@university.edu.vn"].verified_at is None
            assert users["disabled@university.edu.vn"].status == "disabled"
            assert db.scalar(select(AccountToken)).consumed_at is not None
        command.check(config)
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_conversation_migration_preserves_existing_messages_and_citations(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'legacy_history.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_engine(url)
    try:
        command.upgrade(config, "d72a08b1ee51")
        when = utcnow()
        with Session(engine) as db:
            user = User(email="legacy@university.edu.vn", name="Legacy", password_hash="old-hash", status="active")
            db.add(user)
            db.flush()
            db.execute(text("INSERT INTO conversations (id,user_id,title,created_at,updated_at) "
                            "VALUES (:id,:user_id,:title,:now,:now)"),
                       {"id": "legacy-conversation", "user_id": user.id, "title": "Old title", "now": when})
            for message_id, role, content, citations in [
                ("message-1", "user", "Old question", None),
                ("message-2", "assistant", "Old answer", [{"quote": "Original quote"}]),
            ]:
                db.execute(text("INSERT INTO messages (id,conversation_id,role,content,citations,status,created_at) "
                                "VALUES (:id,'legacy-conversation',:role,:content,:citations,:status,:now)"),
                           {"id": message_id, "role": role, "content": content,
                            "citations": json.dumps(citations) if citations is not None else None,
                            "status": "answered" if role == "assistant" else None, "now": when})
            db.commit()
        command.upgrade(config, "head")
        with Session(engine) as db:
            messages = list(db.scalars(select(Message).order_by(Message.sequence)))
            assert [(message.content, message.sequence) for message in messages] == [("Old question", 1), ("Old answer", 2)]
            assert messages[1].citations == [{"quote": "Original quote"}]
            assert all(message.delivery_state == "completed" for message in messages)
        command.check(config)
        command.downgrade(config, "d72a08b1ee51")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM messages")) == 2
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        get_settings.cache_clear()


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_document_migration_roundtrip_preserves_accounts_and_provenance(tmp_path, monkeypatch, backend):
    schema = "document_migration_" + uuid.uuid4().hex
    admin_engine = None
    if backend == "postgresql":
        url = os.getenv("AUTH_TEST_DATABASE_URL")
        if not url:
            pytest.skip("PostgreSQL migration acceptance requires AUTH_TEST_DATABASE_URL")
        from sqlalchemy.engine import make_url
        admin_engine = create_engine(url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    else:
        url = f"sqlite:///{tmp_path / 'documents_migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_engine(url)
    try:
        command.upgrade(config, "e3f90124a8c7")
        with Session(engine) as db, db.begin():
            db.add(User(email="preserved@university.edu.vn", name="Existing account", password_hash="unchanged"))
        command.upgrade(config, "head")
        assert {"documents", "document_versions", "document_audit"} <= set(inspect(engine).get_table_names())
        with Session(engine) as db, db.begin():
            assert import_manifest(db, ROOT / "data/manifest.csv")["created"] == 21
            assert seed_demo_accounts(db, get_settings()) == 2
        # Exercise the handoff starting from migrated tables, not create_all().
        from fastapi.testclient import TestClient
        from api.app import app
        from api.database import get_db
        from tests.test_auth import HEADERS, PASSWORD

        def database():
            with Session(engine) as db:
                yield db

        previous_overrides = dict(app.dependency_overrides)
        app.dependency_overrides[get_db] = database
        try:
            with closing(TestClient(app, headers=HEADERS)) as client:
                auth = client.post("/api/auth/login", json={"email": "admin@university.edu.vn",
                                                           "password": "admin-demo-local-2026"})
                assert auth.status_code == 200
                client.headers["X-CSRF-Token"] = auth.json()["csrfToken"]
                docs = client.get("/api/admin/documents")
                assert docs.status_code == 200 and docs.headers["X-Total-Count"] == "21"
                conversation = client.post("/api/chat/conversations", json={})
                assert conversation.status_code == 201
                conversation_id = conversation.json()["id"]
                assert client.get(f"/api/chat/conversations/{conversation_id}/messages").json() == []
                assert client.post("/api/auth/register", json={"name": "Fresh user",
                    "email": "fresh@university.edu.vn", "password": PASSWORD}).status_code == 201
                auth = client.post("/api/auth/login", json={"email": "fresh@university.edu.vn", "password": PASSWORD})
                assert auth.status_code == 200
                assert client.get("/api/admin/documents").status_code == 403
                assert client.get(f"/api/chat/conversations/{conversation_id}").status_code == 404
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)
        command.check(config)
        with Session(engine) as db:
            doc = db.scalar(select(Document).where(Document.legacy_doc_id == "iu-scse-handbook-2024"))
            version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id))
            assert version.version_label == "2024-2025" and version.processing_status is None
            assert version.manifest_metadata["role"] == "indexed"
        command.downgrade(config, "e3f90124a8c7")
        assert "documents" not in inspect(engine).get_table_names()
        with Session(engine) as db:
            assert db.scalar(select(User).where(User.email == "preserved@university.edu.vn")).password_hash == "unchanged"
        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()
        if admin_engine:
            with admin_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin_engine.dispose()
        get_settings.cache_clear()
