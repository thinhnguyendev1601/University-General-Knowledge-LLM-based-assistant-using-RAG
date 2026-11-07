"""Account flows use real SQL transactions/hashing, with mail captured at the adapter."""
from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.orm import Session

from api.app import app
from api.auth_security import cookie_name, digest, password_hasher
from api.database import get_db
from api.mail import MailDeliveryError, get_mailer
from api.models import AccountToken, Base, LoginSession, User, utcnow
from api.settings import Settings, get_settings

PASSWORD = "a sufficiently long password"
EMAIL = "student@university.edu.vn"
HEADERS = {"Origin": "http://localhost:5173", "X-Requested-With": "XMLHttpRequest"}


class CapturedMail:
    def __init__(self):
        self.messages = []
        self.fail = False

    def send_password_reset(self, email, token):
        if self.fail:
            raise MailDeliveryError("test failure")
        self.messages.append((email, "reset", token))


@pytest.fixture
def account(tmp_path):
    url = os.getenv("AUTH_TEST_DATABASE_URL")
    schema = "auth_test_" + uuid.uuid4().hex
    if url:
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    else:
        engine = create_engine(f"sqlite:///{tmp_path / 'accounts.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    settings = Settings(rag_enabled=False)
    mail = CapturedMail()

    def database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_mailer] = lambda: mail
    # No context manager: account tests must not download/load the RAG models.
    client = TestClient(app, headers=HEADERS)
    yield client, engine, mail
    client.close()
    app.dependency_overrides.clear()
    if url:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


def register(client, email=EMAIL, **extra):
    return client.post("/api/auth/register", json={"name": "Student", "email": email, "password": PASSWORD, **extra})


def activate(client, mail):
    assert register(client).status_code == 201
    assert not mail.messages


def login(client, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": EMAIL, "password": password})


@pytest.mark.parametrize("email", ["x@gmail.com", "x@cs.university.edu.vn", "x@university.edu.vn.evil.com", "x@@university.edu.vn", "not-an-email"])
def test_registration_rejects_other_domains_and_invalid_addresses(account, email):
    client, engine, mail = account
    assert register(client, email).status_code == 422
    assert not mail.messages
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


def test_registration_normalizes_email_and_stores_only_hashes(account):
    client, engine, mail = account
    response = register(client, "  Student@UNIVERSITY.EDU.VN  ")
    assert response.status_code == 201
    assert "token" not in response.json()
    assert not mail.messages
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.email == EMAIL and user.role == "user" and user.status == "active"
        assert user.verified_at is None
        assert user.password_hash.startswith("$argon2id$")
        assert password_hasher.verify(user.password_hash, PASSWORD)
        assert db.scalar(select(func.count()).select_from(AccountToken)) == 0
    assert response.headers["cache-control"] == "no-store"


def test_duplicate_email_does_not_overwrite_password_or_send_new_token(account):
    client, engine, mail = account
    original = register(client)
    duplicate = register(client, "STUDENT@university.edu.vn", password="a different long password")
    assert original.status_code == 201 and duplicate.status_code == 409
    assert not mail.messages
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert password_hasher.verify(db.scalar(select(User)).password_hash, PASSWORD)


def test_extra_role_and_short_password_are_rejected_without_echoing_secrets(account):
    client, _, _ = account
    assert register(client, role="admin").status_code == 422
    response = register(client, password="SECRET-short")
    assert response.status_code == 422 and "SECRET-short" not in response.text


def test_registration_allows_immediate_login_without_mailbox_verification(account):
    client, engine, mail = account
    register(client)
    assert login(client).status_code == 200
    assert client.get("/api/auth/me").status_code == 200
    assert not mail.messages
    with Session(engine) as db:
        user = db.scalar(select(User))
        assert user.status == "active" and user.verified_at is None


def test_expired_reset_and_legacy_verification_tokens_are_rejected(account):
    client, engine, mail = account
    register(client)
    assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).status_code == 202
    token = mail.messages[-1][2]
    with Session(engine) as db:
        db.execute(update(AccountToken).values(expires_at=utcnow() - timedelta(seconds=1)))
        db.commit()
        user = db.scalar(select(User))
        legacy = "legacy-verification-token-with-enough-entropy"
        db.add(AccountToken(user_id=user.id, token_hash=digest(legacy), purpose="verify",
                            expires_at=utcnow() + timedelta(minutes=30)))
        db.commit()
    assert client.post("/api/auth/reset-password", json={"token": token, "password": PASSWORD}).status_code == 400
    assert client.post("/api/auth/reset-password", json={"token": legacy, "password": PASSWORD}).status_code == 400


def test_requesting_another_reset_invalidates_previous_token(account):
    client, engine, mail = account
    register(client)
    assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).status_code == 202
    old = mail.messages[-1][2]
    assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).status_code == 202
    assert len(mail.messages) == 2
    assert client.post("/api/auth/reset-password", json={"token": old, "password": PASSWORD}).status_code == 400
    assert client.post("/api/auth/reset-password", json={"token": mail.messages[-1][2], "password": PASSWORD}).status_code == 200


def test_registration_does_not_depend_on_smtp(account):
    client, engine, mail = account
    mail.fail = True
    assert register(client).status_code == 201
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(AccountToken)) == 0
    assert login(client).status_code == 200


def test_failed_reset_email_preserves_previous_working_token(account):
    client, engine, mail = account
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    old = mail.messages[-1][2]
    mail.fail = True
    assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).status_code == 503
    assert client.post("/api/auth/reset-password", json={"token": old, "password": PASSWORD}).status_code == 200


@pytest.mark.skipif(not os.getenv("AUTH_TEST_DATABASE_URL"), reason="PostgreSQL row-lock concurrency check")
def test_only_one_concurrent_reset_request_consumes_the_token(account):
    client, _, mail = account
    register(client)
    client.post("/api/auth/forgot-password", json={"email": EMAIL})
    token = mail.messages[-1][2]

    def reset():
        other = TestClient(app, headers=HEADERS)
        try:
            return other.post("/api/auth/reset-password", json={"token": token, "password": PASSWORD}).status_code
        finally:
            other.close()

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(lambda _: reset(), range(2))) == [200, 400]


def test_verification_endpoints_are_removed(account):
    client, _, _ = account
    assert client.post("/api/auth/verify-email", json={"token": "unused"}).status_code == 404
    assert client.post("/api/auth/resend-verification", json={"email": EMAIL}).status_code == 404


def test_cookie_login_restore_logout_and_replayed_cookie(account):
    client, engine, mail = account
    activate(client, mail)
    response = login(client)
    assert response.status_code == 200
    assert {"user", "csrfToken", "expiresAt"} == response.json().keys()
    assert "HttpOnly" in response.headers["set-cookie"] and "SameSite=lax" in response.headers["set-cookie"]
    raw_cookie = client.cookies.get("university_session")
    with Session(engine) as db:
        assert db.get(LoginSession, digest(raw_cookie))
        assert not db.get(LoginSession, raw_cookie)
    csrf = response.json()["csrfToken"]
    assert client.get("/api/auth/me").json()["user"]["email"] == EMAIL
    restored = TestClient(app, headers=HEADERS)
    restored.cookies.set("university_session", raw_cookie)
    assert restored.get("/api/auth/me").status_code == 200
    restored.close()
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("university_session", raw_cookie)
    assert client.get("/api/auth/me").status_code == 401


def test_unsafe_requests_require_origin_and_session_csrf(account):
    client, _, mail = account
    assert client.post("/api/auth/register", json={"email": EMAIL, "name": "Student", "password": PASSWORD},
                       headers={"Origin": "https://evil.example"}).status_code == 403
    activate(client, mail)
    login(client)
    assert client.post("/api/auth/logout", json={}).status_code == 403
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.get("/api/auth/me").status_code == 200


@pytest.mark.parametrize("field", ["expires_at", "last_seen_at"])
def test_absolute_and_idle_session_expiry(account, field):
    client, engine, mail = account
    activate(client, mail)
    login(client)
    with Session(engine) as db:
        db.execute(update(LoginSession).values(**{field: utcnow() - timedelta(days=1)}))
        db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_login_rotates_old_cookie_and_disabled_accounts_lose_access(account):
    client, engine, mail = account
    activate(client, mail)
    assert login(client).status_code == 200
    old = client.cookies.get("university_session")
    assert login(client).status_code == 200
    assert client.cookies.get("university_session") != old
    replay = TestClient(app, headers=HEADERS)
    replay.cookies.set("university_session", old)
    assert replay.get("/api/auth/me").status_code == 401
    replay.close()
    with Session(engine) as db:
        db.execute(update(User).values(status="disabled"))
        db.commit()
    assert client.get("/api/auth/me").status_code == 401
    assert login(client).status_code == 401


def test_reset_password_revokes_sessions_and_token_cannot_be_reused(account):
    client, _, mail = account
    activate(client, mail)
    login(client)
    response = client.post("/api/auth/forgot-password", json={"email": EMAIL})
    assert response.status_code == 202
    token = mail.messages[-1][2]
    new_password = "a brand new long password"
    assert client.post("/api/auth/reset-password", json={"token": token, "password": new_password}).status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/reset-password", json={"token": token, "password": PASSWORD}).status_code == 400
    assert login(client).status_code == 401
    assert login(client, new_password).status_code == 200


def test_unknown_reset_is_generic_and_rate_limits_persist(account):
    client, _, mail = account
    unknown = {"email": "unknown@university.edu.vn"}
    responses = [client.post("/api/auth/forgot-password", json=unknown) for _ in range(4)]
    assert [response.status_code for response in responses] == [202, 202, 202, 429]
    assert "Retry-After" in responses[-1].headers
    assert not mail.messages


def test_chat_api_requires_real_session(account):
    client, _, _ = account
    response = client.post("/api/chat/messages", json={"conversationId": "c1", "content": "hello"})
    assert response.status_code == 401


def test_secure_cookie_configuration(account):
    client, _, mail = account
    activate(client, mail)
    settings = replace(Settings(), frontend_url="https://university.example", cookie_secure=True)
    app.dependency_overrides[get_settings] = lambda: settings
    response = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD},
                           headers={"Origin": settings.origin})
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(cookie_name(settings)) and "Secure" in cookie and "HttpOnly" in cookie
