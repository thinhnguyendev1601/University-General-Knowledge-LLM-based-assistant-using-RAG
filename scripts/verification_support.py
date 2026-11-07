"""Disposable local PostgreSQL databases for release verification, never the app DB."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from api.settings import ROOT


def drop_test_database(base_url, name):
    if not re.fullmatch(r"university_(?:b7|restore)_[a-z0-9_]{1,40}", name):
        raise ValueError("Refusing to drop a database outside the test namespace")
    url = make_url(base_url)
    if name == url.database:
        raise ValueError("Refusing to drop the configured source database")
    if url.host not in {"localhost", "127.0.0.1"}:
        raise ValueError("Verification database cleanup is local only")
    engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
    try:
        with engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        engine.dispose()


@contextmanager
def temporary_database(base_url):
    url = make_url(base_url)
    if url.get_backend_name() != 'postgresql' or url.host not in {'localhost','127.0.0.1'}:
        raise ValueError('Verification requires local PostgreSQL')
    name = 'university_b7_' + uuid.uuid4().hex
    admin = create_engine(url.set(database='postgres'), isolation_level='AUTOCOMMIT', hide_parameters=True)
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()
    test_url = url.set(database=name).render_as_string(hide_password=False)
    try:
        env = {**os.environ, 'DATABASE_URL':test_url, 'RAG_ENABLED':'false', 'APP_ENV':'test'}
        result = subprocess.run([sys.executable,'-B','-m','alembic','upgrade','head'], cwd=ROOT,
                                env=env, capture_output=True, timeout=60)
        if result.returncode:
            raise RuntimeError('Migration failed in disposable verification database')
        yield test_url
    finally:
        drop_test_database(base_url, name)
