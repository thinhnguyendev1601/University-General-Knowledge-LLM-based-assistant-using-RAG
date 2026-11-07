from alembic import context
from sqlalchemy import create_engine, pool

from api.models import Base
from api.settings import get_settings

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=get_settings().database_url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    url = get_settings().database_url
    options = {"connect_timeout": 5} if url.startswith("postgresql") else {}
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True, connect_args=options)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
