"""HTTP-level cache tests, including stale snapshots, DB guards and Redis outages."""
from dataclasses import replace
from datetime import timedelta
import json
import logging
import os
import uuid

from fastapi.testclient import TestClient
import pytest
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy import event, select, update
from sqlalchemy.orm import Session

from api.app import app
from api.auth_security import digest
from api.models import LoginSession, User, utcnow
from api.session_cache import (
    RedisSessionCache, SessionSnapshot, close_session_caches, get_session_cache,
)
from api.settings import Settings
from tests.test_auth import account, activate, login, HEADERS, EMAIL, PASSWORD


class MemoryRedis:
    def __init__(self):
        self.data = {}
        self.ttls = {}
        self.broken = False
        self.calls = 0

    def _check(self):
        self.calls += 1
        if self.broken:
            raise RedisConnectionError("redis://private-user:private-password@private-host")

    def get(self, key):
        self._check()
        return self.data.get(key)

    def set(self, key, value, *, ex):
        self._check()
        self.data[key] = value
        self.ttls[key] = ex
        return True

    def delete(self, *keys):
        self._check()
        for key in keys:
            self.data.pop(key, None)
            self.ttls.pop(key, None)

    def close(self):
        pass


@pytest.fixture
def cached_account(account):
    client, engine, mail = account
    redis = MemoryRedis()
    clock = [100.0]
    cache = RedisSessionCache(redis, "test-session:" + uuid.uuid4().hex + ":", 60,
                             clock=lambda: clock[0])
    app.dependency_overrides[get_session_cache] = lambda: cache
    activate(client, mail)
    assert login(client).status_code == 200
    return client, engine, mail, cache, redis, clock


def cached_cookie(client, cache):
    raw = client.cookies.get("university_session")
    return raw, cache.key(digest(raw))


def session_selects(statements):
    return [sql for sql in statements
            if sql.lstrip().lower().startswith("select") and "from sessions" in sql.lower()]


def test_hit_avoids_session_select_but_preserves_database_guard(cached_account):
    client, engine, _, cache, redis, _ = cached_account
    _, key = cached_cookie(client, cache)
    assert key in redis.data
    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        hit = client.get("/api/auth/me")
        assert hit.status_code == 200
        assert not session_selects(statements)
        assert any(sql.lower().startswith("update sessions") for sql in statements)
        redis.delete(key)
        statements.clear()
        miss = client.get("/api/auth/me")
        assert miss.json() == hit.json()
        assert len(session_selects(statements)) == 1
        assert key in redis.data
    finally:
        event.remove(engine, "before_cursor_execute", record)


def test_cache_contains_no_password_or_raw_session_cookie(cached_account, caplog):
    client, _, _, cache, redis, _ = cached_account
    raw, key = cached_cookie(client, cache)
    value = json.loads(redis.data[key])
    assert set(value) == {"version", "userId", "csrfToken", "expiresAt"}
    assert raw not in key and raw not in redis.data[key] and PASSWORD not in redis.data[key]
    assert 0 < redis.ttls[key] <= 60
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        assert client.get("/api/auth/me").status_code == 200
    assert '"outcome":"hit"' in caplog.text
    assert all(secret not in caplog.text for secret in (raw, value["csrfToken"], PASSWORD))


@pytest.mark.parametrize("field", ["expires_at", "last_seen_at", "revoked_at"])
def test_warm_cache_cannot_override_database_expiry_or_revocation(cached_account, field):
    client, engine, _, cache, redis, _ = cached_account
    raw, key = cached_cookie(client, cache)
    with Session(engine) as db, db.begin():
        db.execute(update(LoginSession).where(LoginSession.id == digest(raw))
                   .values(**{field: utcnow() - timedelta(days=1)}))
    assert key in redis.data
    assert client.get("/api/auth/me").status_code == 401
    assert key not in redis.data


def test_cache_hit_updates_activity_without_moving_it_backwards(cached_account):
    client, engine, _, cache, _, _ = cached_account
    raw, _ = cached_cookie(client, cache)
    session_id = digest(raw)
    before = utcnow()
    with Session(engine) as db, db.begin():
        db.execute(update(LoginSession).where(LoginSession.id == session_id)
                   .values(last_seen_at=before - timedelta(minutes=5)))
    assert client.get("/api/auth/me").status_code == 200
    with Session(engine) as db:
        assert db.get(LoginSession, session_id).last_seen_at.replace(tzinfo=before.tzinfo) >= before
    ahead = utcnow() + timedelta(minutes=1)
    with Session(engine) as db, db.begin():
        db.execute(update(LoginSession).where(LoginSession.id == session_id).values(last_seen_at=ahead))
    assert client.get("/api/auth/me").status_code == 200
    with Session(engine) as db:
        assert db.get(LoginSession, session_id).last_seen_at.replace(tzinfo=ahead.tzinfo) == ahead


def test_status_and_role_are_always_read_from_database(cached_account):
    client, engine, _, cache, redis, _ = cached_account
    _, key = cached_cookie(client, cache)
    with Session(engine) as db, db.begin():
        db.execute(update(User).where(User.email == EMAIL).values(role="admin"))
    assert client.get("/api/admin/documents").status_code == 200
    with Session(engine) as db, db.begin():
        db.execute(update(User).where(User.email == EMAIL).values(role="user"))
    assert client.get("/api/admin/documents").status_code == 403
    with Session(engine) as db, db.begin():
        db.execute(update(User).where(User.email == EMAIL).values(status="disabled"))
    assert client.get("/api/auth/me").status_code == 401
    assert key not in redis.data


def test_invalid_csrf_or_origin_does_not_extend_session(cached_account):
    client, engine, _, cache, _, _ = cached_account
    raw, _ = cached_cookie(client, cache)
    with Session(engine) as db:
        previous = db.get(LoginSession, digest(raw)).last_seen_at
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": "wrong"}).status_code == 403
    with Session(engine) as db:
        assert db.get(LoginSession, digest(raw)).last_seen_at == previous
    csrf = client.get("/api/auth/me").json()["csrfToken"]
    with Session(engine) as db:
        previous = db.get(LoginSession, digest(raw)).last_seen_at
    assert client.post("/api/auth/logout", json={}, headers={
        "Origin": "https://evil.example", "X-CSRF-Token": csrf}).status_code == 403
    with Session(engine) as db:
        assert db.get(LoginSession, digest(raw)).last_seen_at == previous


def test_logout_rejects_stale_cache_refilled_after_invalidation(cached_account):
    client, _, _, cache, redis, _ = cached_account
    raw, key = cached_cookie(client, cache)
    stale = redis.data[key]
    csrf = client.get("/api/auth/me").json()["csrfToken"]
    assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": csrf}).status_code == 204
    assert key not in redis.data
    redis.set(key, stale, ex=60)  # Another request could finish filling after logout.
    client.cookies.set("university_session", raw)
    assert client.get("/api/auth/me").status_code == 401


def test_login_rotation_invalidates_old_snapshot(cached_account):
    client, _, _, cache, redis, _ = cached_account
    raw, key = cached_cookie(client, cache)
    stale = redis.data[key]
    assert login(client).status_code == 200
    assert key not in redis.data
    redis.set(key, stale, ex=60)
    replay = TestClient(app, headers=HEADERS)
    try:
        replay.cookies.set("university_session", raw)
        assert replay.get("/api/auth/me").status_code == 401
    finally:
        replay.close()


def test_reset_revokes_all_cached_sessions_and_late_fills(cached_account):
    client, _, mail, cache, redis, _ = cached_account
    raw, first = cached_cookie(client, cache)
    # Avoid TestClient's context manager: it would start the model lifespan.
    other = TestClient(app, headers=HEADERS)
    try:
        assert login(other).status_code == 200
        other_raw, second = cached_cookie(other, cache)
        stale = {first: redis.data[first], second: redis.data[second]}
        assert client.post("/api/auth/forgot-password", json={"email": EMAIL}).status_code == 202
        token = mail.messages[-1][2]
        assert client.post("/api/auth/reset-password", json={
            "token": token, "password": PASSWORD + " changed"}).status_code == 200
        assert first not in redis.data and second not in redis.data
        redis.data.update(stale)
        client.cookies.set("university_session", raw)
        other.cookies.set("university_session", other_raw)
        assert client.get("/api/auth/me").status_code == 401
        assert other.get("/api/auth/me").status_code == 401
    finally:
        other.close()


@pytest.mark.parametrize("value", ["{broken json", "[]", '{"version":99}', "x" * 4097])
def test_corrupt_cache_falls_back_to_database(cached_account, value):
    client, _, _, cache, redis, _ = cached_account
    _, key = cached_cookie(client, cache)
    redis.data[key] = value
    assert client.get("/api/auth/me").status_code == 200
    assert json.loads(redis.data[key])["version"] == 1


@pytest.mark.parametrize("field,value", [("userId", "another-user"), ("csrfToken", "forged-token")])
def test_forged_cache_identity_or_csrf_never_authorizes(cached_account, field, value):
    client, _, _, cache, redis, _ = cached_account
    _, key = cached_cookie(client, cache)
    payload = json.loads(redis.data[key])
    payload[field] = value
    redis.data[key] = json.dumps(payload)
    assert client.get("/api/auth/me").status_code == 401


def test_redis_outage_preserves_auth_logout_and_recovery(cached_account, caplog):
    client, _, _, cache, redis, clock = cached_account
    raw, key = cached_cookie(client, cache)
    redis.broken = True
    calls = redis.calls
    with caplog.at_level(logging.INFO, logger="uvicorn.error"):
        response = client.get("/api/auth/me")
        assert response.status_code == 200
        assert redis.calls == calls + 1  # Failed read suppresses another failed write.
        csrf = response.json()["csrfToken"]
        assert client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": csrf}).status_code == 204
    assert "private-password" not in caplog.text and "private-host" not in caplog.text
    assert key in redis.data  # Invalidation was unavailable; DB revocation must suffice.
    redis.broken = False
    clock[0] += 6
    client.cookies.set("university_session", raw)
    assert client.get("/api/auth/me").status_code == 401
    assert key not in redis.data


def test_cached_session_cannot_authenticate_without_database(cached_account, monkeypatch):
    client, engine, _, _, _, _ = cached_account
    from sqlalchemy.exc import SQLAlchemyError
    original = Session.execute

    def unavailable(self, *args, **kwargs):
        if self.get_bind() is engine:
            raise SQLAlchemyError("private database connection")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Session, "execute", unavailable)
    response = client.get("/api/auth/me")
    assert response.status_code == 503 and "private database" not in response.text


def test_ttl_is_capped_at_absolute_expiry_and_expired_entries_are_not_written():
    redis = MemoryRedis()
    cache = RedisSessionCache(redis, "ttl-test:", 60)
    snapshot = SessionSnapshot("a" * 64, str(uuid.uuid4()), "csrf", utcnow() + timedelta(seconds=20))
    cache.store(snapshot)
    assert 0 < redis.ttls[cache.key(snapshot.id)] <= 20
    cache.store(replace(snapshot, id="b" * 64, expires_at=utcnow() - timedelta(seconds=1)))
    assert cache.key("b" * 64) not in redis.data


@pytest.mark.parametrize("changes", [
    {"session_cache_ttl_seconds": 0}, {"session_cache_ttl_seconds": 3601},
    {"redis_timeout_seconds": 0}, {"redis_timeout_seconds": float("inf")},
    {"redis_url": "http://localhost:56379"}, {"redis_url": "redis://localhost:bad"},
    {"redis_url": "redis://localhost/0?socket_timeout=999"},
    {"redis_url": "redis://localhost/not-a-database"},
])
def test_invalid_cache_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        Settings(session_cache_enabled=True, **changes)


def test_cache_is_optional_and_database_namespaces_are_isolated(monkeypatch):
    assert get_session_cache(Settings()) is None
    monkeypatch.setattr(Redis, "from_url", lambda *args, **kwargs: MemoryRedis())
    try:
        first = get_session_cache(Settings(session_cache_enabled=True, database_url="sqlite:///first.db"))
        second = get_session_cache(Settings(session_cache_enabled=True, database_url="sqlite:///second.db"))
        assert first.key("a" * 64) != second.key("a" * 64)
    finally:
        close_session_caches()


@pytest.mark.skipif(not os.getenv("SESSION_CACHE_TEST_REDIS_URL"), reason="Opt-in real Redis")
def test_real_redis_hit_miss_ttl_and_revocation(account):
    client, engine, mail = account
    redis = Redis.from_url(os.environ["SESSION_CACHE_TEST_REDIS_URL"], decode_responses=True,
                           socket_timeout=1, socket_connect_timeout=1)
    namespace = "university:session-test:" + uuid.uuid4().hex + ":"
    cache = RedisSessionCache(redis, namespace, 60)
    app.dependency_overrides[get_session_cache] = lambda: cache
    try:
        assert redis.ping()
        activate(client, mail)
        assert login(client).status_code == 200
        raw, key = cached_cookie(client, cache)
        assert redis.exists(key) and 0 < redis.ttl(key) <= 60
        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        event.listen(engine, "before_cursor_execute", record)
        try:
            response = client.get("/api/auth/me")
            assert response.status_code == 200 and not session_selects(statements)
            redis.delete(key)
            statements.clear()
            assert client.get("/api/auth/me").status_code == 200
            assert len(session_selects(statements)) == 1
        finally:
            event.remove(engine, "before_cursor_execute", record)
        stale = redis.get(key)
        assert client.post("/api/auth/logout", json={}, headers={
            "X-CSRF-Token": response.json()["csrfToken"]}).status_code == 204
        assert not redis.exists(key)
        redis.set(key, stale, ex=60)
        client.cookies.set("university_session", raw)
        assert client.get("/api/auth/me").status_code == 401
    finally:
        owned = list(redis.scan_iter(match=namespace + "*"))
        if owned:
            redis.delete(*owned)
        redis.close()
