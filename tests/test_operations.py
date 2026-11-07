"""Health isolation, secret-free logs and cleanup that preserves active users/content."""
from dataclasses import replace
from datetime import timedelta
import json
import logging
import os
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.app import app
from api.auth_security import digest, RATE_LIMIT_WINDOW_SECONDS
from api.health import expected_revision, get_probe_engine, probe_provider, _provider_cache
from api.models import AccountToken, Conversation, LoginSession, Message, RateLimit, User, utcnow
from api.rag_runtime import STATE
from api.settings import Settings, get_settings
from api.telemetry import AccessPathFilter
from scripts.maintenance import cleanup, temporary_files
from tests.test_auth import account


@pytest.fixture
def operational(account):
    client, engine, _ = account
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        connection.execute(text("INSERT INTO alembic_version VALUES (:revision)"), {"revision": expected_revision()})
    app.dependency_overrides[get_probe_engine] = lambda: engine
    return client, engine


def test_liveness_and_account_mode_readiness_do_not_require_model(operational):
    client, _ = operational
    assert client.get('/api/health/live').json() == {"status": "alive"}
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert response.json()["components"] == {"database": "ready", "rag": "disabled", "model": "disabled"}
    assert response.headers['cache-control'] == 'no-store'


def test_readiness_detects_old_schema_without_breaking_liveness(operational):
    client, engine = operational
    with engine.begin() as connection:
        connection.execute(text("UPDATE alembic_version SET version_num='old_revision'"))
    response = client.get('/api/health/ready')
    assert response.status_code == 503 and response.json()['components']['database'] == 'migration_required'
    assert client.get('/api/health/live').status_code == 200


def test_readiness_handles_db_error_without_exposing_connection(operational):
    client, _ = operational

    class BrokenEngine:
        def connect(self):
            raise RuntimeError('password=must-never-appear')

    app.dependency_overrides[get_probe_engine] = BrokenEngine
    response = client.get('/api/health/ready')
    assert response.status_code == 503
    assert response.json()['components']['database'] == 'unavailable'
    assert 'must-never-appear' not in response.text
    assert client.get('/api/health/live').status_code == 200


def test_readiness_distinguishes_missing_pipeline_and_provider(operational, monkeypatch):
    client, _ = operational
    app.dependency_overrides[get_settings] = lambda: Settings(rag_enabled=True)
    monkeypatch.delitem(STATE, 'pipe', raising=False)
    assert client.get('/api/health/ready').json()['components']['rag'] == 'not_loaded'
    pipe = SimpleNamespace(index=SimpleNamespace(chunks=[1]), llm=None,
                           answer=lambda *args: pytest.fail('Health must not generate an answer'))
    monkeypatch.setitem(STATE, 'pipe', pipe)
    assert client.get('/api/health/ready').status_code == 200
    monkeypatch.setattr('api.health.probe_provider', lambda _: 'unavailable')
    response = client.get('/api/health/ready')
    assert response.status_code == 503 and response.json()['components']['model'] == 'unavailable'


def test_provider_probe_checks_loaded_model_via_tags_and_caches(monkeypatch):
    _provider_cache.clear()
    calls = []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'{"models":[{"name":"llama3.2:latest"}]}'

    def tags(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr('api.health.urllib.request.urlopen', tags)
    pipe = SimpleNamespace(llm=SimpleNamespace(url='http://127.0.0.1:11434', model='llama3.2'))
    assert probe_provider(pipe) == probe_provider(pipe) == 'ready'
    assert calls == [('http://127.0.0.1:11434/api/tags', 2)]
    pipe.llm.model = 'not-pulled'
    assert probe_provider(pipe) == 'model_missing'
    _provider_cache.clear()


def test_request_ids_and_logs_never_include_body_cookie_or_query(operational, caplog):
    client, _ = operational
    request_id = str(uuid.uuid4())
    with caplog.at_level(logging.INFO, logger='uvicorn.error'):
        response = client.post('/api/auth/login?token=query-secret-marker',
            json={'email':'nobody@university.edu.vn','password':'password-secret-marker'},
            headers={'X-Request-Id':request_id,'Cookie':'university_session=cookie-secret-marker'})
    assert response.status_code == 401 and response.headers['X-Request-Id'] == request_id
    assert 'http_request' in caplog.text and request_id in caplog.text
    assert all(secret not in caplog.text for secret in ('query-secret-marker','password-secret-marker','cookie-secret-marker'))
    invalid = client.get('/api/health/live', headers={'X-Request-Id':'not-a-uuid'})
    assert str(uuid.UUID(invalid.headers['X-Request-Id'])) == invalid.headers['X-Request-Id']
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 1, '%s %s %s %s %s',
                               ('client','GET','/api/auth/me?token=secret','1.1',200), None)
    assert AccessPathFilter().filter(record)
    assert 'token=secret' not in record.getMessage()


def test_cleanup_dry_run_apply_idempotence_and_active_session(account):
    client, engine, _ = account
    now = utcnow()
    settings = Settings(rag_enabled=False)
    current_window = int(now.timestamp()) // RATE_LIMIT_WINDOW_SECONDS * RATE_LIMIT_WINDOW_SECONDS
    with Session(engine) as db, db.begin():
        user = User(email='cleanup@university.edu.vn',name='Keep',password_hash='unused')
        db.add(user); db.flush()
        for name, fields in {
            'active':{}, 'expired':{'expires_at':now-timedelta(seconds=1)},
            'idle':{'last_seen_at':now-timedelta(seconds=settings.session_idle_seconds+1)},
            'revoked_old':{'revoked_at':now-timedelta(days=2)},
            'revoked_recent':{'revoked_at':now-timedelta(minutes=1)},
        }.items():
            data={'id':digest(name),'user_id':user.id,'csrf_token':'csrf','expires_at':now+timedelta(hours=1),
                  'last_seen_at':now,**fields}
            db.add(LoginSession(**data))
        for index, fields in enumerate(({'expires_at':now-timedelta(seconds=1)},
              {'consumed_at':now-timedelta(days=2)}, {'consumed_at':now-timedelta(minutes=1)}, {})):
            db.add(AccountToken(user_id=user.id,token_hash=f'{index:064x}',purpose='reset',
                **{'expires_at':now+timedelta(hours=1),'consumed_at':None,**fields}))
        for index, start in enumerate((current_window-900,current_window,current_window+900)):
            db.add(RateLimit(key=str(index),window_start=start,count=3))
        conversation=Conversation(user_id=user.id,title='Keep history')
        db.add(conversation); db.flush()
        db.add(Message(conversation_id=conversation.id,role='user',content='Keep content',sequence=1))
        conversation_id=conversation.id
    with Session(engine) as db, db.begin():
        expected={'sessions':3,'accountTokens':2,'rateLimits':1}
        assert cleanup(db,settings,now=now) == expected
        assert db.scalar(select(func.count()).select_from(LoginSession)) == 5
    with Session(engine) as db, db.begin():
        assert cleanup(db,settings,apply=True,now=now) == expected
    with Session(engine) as db, db.begin():
        assert cleanup(db,settings,apply=True,now=now) == dict.fromkeys(expected,0)
        assert db.scalar(select(Message)).content == 'Keep content'
        assert db.scalar(select(Conversation)).title == 'Keep history'
        assert db.scalar(select(User)).name == 'Keep'
        assert db.get(RateLimit,'1').count == 3
    client.cookies.set('university_session','active')
    assert client.get('/api/auth/me').status_code == 200
    assert client.get(f'/api/chat/conversations/{conversation_id}/messages').json()[0]['content'] == 'Keep content'


def test_file_cleanup_only_selects_old_server_generated_regular_files(tmp_path):
    now=utcnow()
    old=tmp_path/('tmp-'+uuid.uuid4().hex+'.part'); old.write_text('partial')
    recent=tmp_path/('tmp-'+uuid.uuid4().hex+'.part'); recent.write_text('active')
    unrelated=tmp_path/'original.pdf'; unrelated.write_text('keep')
    nested=tmp_path/'nested'; nested.mkdir()
    nested_file=nested/('tmp-'+uuid.uuid4().hex+'.part'); nested_file.write_text('keep')
    for path in (old, unrelated, nested_file):
        os.utime(path,(now.timestamp()-90000,)*2)
    assert temporary_files(tmp_path,now) == [old]
    assert recent.exists() and unrelated.exists() and nested_file.exists()


def test_smtp_accepted_but_db_commit_failed_keeps_old_token_valid(account):
    client,engine,mail=account
    email='commit@university.edu.vn'
    password='a sufficiently long password'
    assert client.post('/api/auth/register',json={'name':'Commit test','email':email,'password':password}).status_code==201
    assert client.post('/api/auth/forgot-password',json={'email':email}).status_code==202
    old=mail.messages[-1][2]

    def fail_after_send(session):
        if len(mail.messages)==2:
            raise SQLAlchemyError('do not expose private database state')

    event.listen(Session,'before_commit',fail_after_send)
    try:
        response=client.post('/api/auth/forgot-password',json={'email':email})
        assert response.status_code==503 and 'private database' not in response.text
    finally:
        event.remove(Session,'before_commit',fail_after_send)
    assert len(mail.messages)==2  # SMTP cannot be rolled back after acceptance.
    with Session(engine) as db:
        assert db.scalar(select(AccountToken).where(AccountToken.token_hash==digest(mail.messages[1][2]))) is None
        assert db.scalar(select(AccountToken).where(AccountToken.token_hash==digest(old))).consumed_at is None
    assert client.post('/api/auth/reset-password',json={'token':old,'password':password+' changed'}).status_code==200


def test_probe_pool_preserves_configured_schema_and_limits_waits(monkeypatch):
    import api.health as health
    health.get_probe_engine.cache_clear()
    captured={}
    def engine(url,**options):
        captured.update(options)
        return object()
    monkeypatch.setattr(health,'get_settings',lambda:Settings(database_url='postgresql+psycopg://u:p@localhost/db?options=-csearch_path%3Dcustom'))
    monkeypatch.setattr(health,'create_engine',engine)
    try:
        health.get_probe_engine()
        assert '-csearch_path=custom' in captured['connect_args']['options']
        assert 'statement_timeout=2000' in captured['connect_args']['options']
        assert captured['pool_timeout']==1 and captured['max_overflow']==0
    finally:
        health.get_probe_engine.cache_clear()
