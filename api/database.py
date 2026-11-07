from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from api.settings import get_settings


@lru_cache
def get_engine():
    url = get_settings().database_url
    options = {"connect_timeout": 5} if url.startswith("postgresql") else {}
    return create_engine(url, pool_pre_ping=True, hide_parameters=True, connect_args=options)


def get_db():
    with Session(get_engine()) as db:
        yield db
