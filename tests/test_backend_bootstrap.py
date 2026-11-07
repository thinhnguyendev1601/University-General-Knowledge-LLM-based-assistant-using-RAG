"""B0 environment, development seed and retained login attempt policy."""
from dataclasses import replace

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth_security import password_hasher
from api.models import User
from api.settings import Settings
from scripts.seed_demo_accounts import DEMO_ACCOUNTS, seed_demo_accounts
from tests.test_auth import account, login, register


def test_demo_seed_is_repeatable_and_preserves_existing_account(account):
    _, engine, _ = account
    settings = Settings(database_url=str(engine.url))
    with Session(engine) as db, db.begin():
        existing = User(email="admin@university.edu.vn", name="Keep me", role="user", status="disabled",
                        password_hash="existing-password-hash")
        db.add(existing)
    with Session(engine) as db, db.begin():
        assert seed_demo_accounts(db, settings) == 1
    with Session(engine) as db, db.begin():
        assert seed_demo_accounts(db, settings) == 0
    with Session(engine) as db:
        existing = db.scalar(select(User).where(User.email == "admin@university.edu.vn"))
        assert (existing.name, existing.role, existing.status, existing.password_hash) == (
            "Keep me", "user", "disabled", "existing-password-hash")
        user = db.scalar(select(User).where(User.email == "user@university.edu.vn"))
        assert user.role == "user" and user.status == "active" and user.verified_at is None
        password_hasher.verify(user.password_hash, DEMO_ACCOUNTS[1][3])


@pytest.mark.parametrize("changes", [
    {"app_env": "test"},
    {"app_env": "production", "frontend_url": "https://university.example", "cookie_secure": True},
    {"frontend_url": "https://university.example", "cookie_secure": True},
    {"database_url": "postgresql+psycopg://demo:secret@database.example/demo"},
])
def test_demo_seed_rejects_nonlocal_or_nondevelopment_environments(account, changes):
    _, engine, _ = account
    settings = replace(Settings(database_url="postgresql+psycopg://demo:secret@localhost/demo"), **changes)
    with pytest.raises(ValueError, match="local development"), Session(engine) as db, db.begin():
        seed_demo_accounts(db, settings)
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(User)) == 0


@pytest.mark.parametrize("changes", [
    {"app_env": "invalid"}, {"app_env": "production"},
    {"app_env": "production", "frontend_url": "https://university.example", "cookie_secure": True},
    {"session_seconds": 0}, {"session_idle_seconds": 0}, {"chat_generation_lease_seconds": 0},
])
def test_environment_rejects_unsafe_production_or_invalid_lifetimes(changes):
    with pytest.raises(ValueError):
        Settings(**changes)


def test_production_accepts_dedicated_credentials_and_secure_origin():
    settings = Settings(app_env="production", frontend_url="https://university.example", cookie_secure=True,
                        database_url="postgresql+psycopg://app:dedicated-secret@database/app")
    assert settings.app_env == "production"


def test_login_keeps_throttling_successful_attempts(account):
    client, _, _ = account
    assert register(client).status_code == 201
    for _ in range(10):
        assert login(client).status_code == 200
    response = login(client)
    assert response.status_code == 429 and 1 <= int(response.headers["Retry-After"]) <= 900
