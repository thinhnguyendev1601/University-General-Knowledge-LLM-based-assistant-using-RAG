"""Explicit, repeatable local development seed. Never run at API startup."""
from urllib.parse import urlsplit

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.auth_security import password_hasher
from api.database import get_engine
from api.models import User
from api.settings import Settings, get_settings

DEMO_ACCOUNTS = (
    ("admin@university.edu.vn", "Demo Admin", "admin", "admin-demo-local-2026"),
    ("user@university.edu.vn", "Demo User", "user", "user-demo-local-2026"),
)


def seed_demo_accounts(db: Session, settings: Settings) -> int:
    database = make_url(settings.database_url)
    if (settings.app_env != "development"
            or urlsplit(settings.frontend_url).hostname not in {"localhost", "127.0.0.1", "::1"}
            or (database.get_backend_name() != "sqlite" and database.host not in {"localhost", "127.0.0.1", "::1"})):
        raise ValueError("Demo accounts are restricted to local development")
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    created = 0
    for email, name, role, password in DEMO_ACCOUNTS:
        statement = insert(User).values(email=email, name=name, role=role, status="active",
                                        password_hash=password_hasher.hash(password))
        result = db.execute(statement.on_conflict_do_nothing(index_elements=[User.email]).returning(User.id))
        created += result.scalar_one_or_none() is not None
    return created


def main():
    settings = get_settings()
    with Session(get_engine()) as db, db.begin():
        created = seed_demo_accounts(db, settings)
    print(f"Created {created} demo accounts; existing accounts were preserved.")


if __name__ == "__main__":
    main()
