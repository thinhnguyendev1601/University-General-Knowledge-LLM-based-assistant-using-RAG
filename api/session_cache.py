"""Optional Redis session snapshots; PostgreSQL still authorizes every request."""
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import math
import time

from fastapi import Depends
from redis import Redis
from redis.backoff import NoBackoff
from redis.exceptions import RedisError
from redis.retry import Retry

from api.models import LoginSession
from api.settings import Settings, get_settings
from api.telemetry import emit


@dataclass(frozen=True)
class SessionSnapshot:
    id: str
    user_id: str
    csrf_token: str
    expires_at: datetime

    @classmethod
    def from_session(cls, session: LoginSession):
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return cls(session.id, session.user_id, session.csrf_token, expires)


class RedisSessionCache:
    def __init__(self, client, namespace: str, ttl_seconds: int, *, clock=time.monotonic):
        self.client = client
        self.namespace = namespace
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self.retry_after = 0.0

    def key(self, session_id: str):
        return self.namespace + session_id

    def _call(self, operation, *args, **kwargs):
        if self.clock() < self.retry_after:
            return None
        try:
            return operation(*args, **kwargs)
        except (RedisError, UnicodeError) as error:
            # Avoid repeated network waits during an outage. Never log URLs or tokens.
            self.retry_after = self.clock() + 5
            emit("session_cache_unavailable", errorType=type(error).__name__)
            return None

    def load(self, session_id: str) -> SessionSnapshot | None:
        raw = self._call(self.client.get, self.key(session_id))
        if raw is None:
            emit("session_cache_lookup", outcome="miss")
            return None
        try:
            if not isinstance(raw, (str, bytes)) or len(raw) > 4096:
                raise ValueError("Invalid cache size")
            data = json.loads(raw)
            if (not isinstance(data, dict) or data.get("version") != 1
                    or not isinstance(data.get("userId"), str) or not 1 <= len(data["userId"]) <= 36
                    or not isinstance(data.get("csrfToken"), str) or not 1 <= len(data["csrfToken"]) <= 64):
                raise ValueError("Invalid cache schema")
            expires = datetime.fromisoformat(data["expiresAt"])
            if expires.tzinfo is None or expires <= datetime.now(timezone.utc):
                raise ValueError("Expired or ambiguous cache timestamp")
            snapshot = SessionSnapshot(session_id, data["userId"], data["csrfToken"], expires)
        except (ValueError, TypeError, KeyError, OverflowError):
            self.invalidate(session_id)
            emit("session_cache_lookup", outcome="invalid")
            return None
        emit("session_cache_lookup", outcome="hit")
        return snapshot

    def store(self, snapshot: SessionSnapshot):
        remaining = math.floor((snapshot.expires_at - datetime.now(timezone.utc)).total_seconds())
        ttl = min(self.ttl_seconds, remaining)
        if ttl <= 0:
            return
        payload = json.dumps({"version": 1, "userId": snapshot.user_id,
                              "csrfToken": snapshot.csrf_token,
                              "expiresAt": snapshot.expires_at.isoformat()}, separators=(",", ":"))
        self._call(self.client.set, self.key(snapshot.id), payload, ex=ttl)

    def invalidate(self, *session_ids: str):
        if session_ids:
            self._call(self.client.delete, *(self.key(value) for value in session_ids))


_clients: set[RedisSessionCache] = set()


@lru_cache(maxsize=8)
def _configured_cache(url: str, database_url: str, ttl: int, timeout: float):
    # DB-specific namespaces prevent snapshots being shared across deployments/schemas.
    scope = hashlib.sha256(database_url.encode()).hexdigest()[:24]
    client = Redis.from_url(url, decode_responses=True, socket_connect_timeout=timeout,
                            socket_timeout=timeout, max_connections=16,
                            retry=Retry(NoBackoff(), 0), protocol=2)
    cache = RedisSessionCache(client, f"university:auth:session:v1:{scope}:", ttl)
    _clients.add(cache)
    return cache


def get_session_cache(settings: Settings = Depends(get_settings)) -> RedisSessionCache | None:
    if not settings.session_cache_enabled:
        return None
    return _configured_cache(settings.redis_url, settings.database_url,
                             min(settings.session_cache_ttl_seconds, settings.session_idle_seconds),
                             settings.redis_timeout_seconds)


def close_session_caches():
    for cache in tuple(_clients):
        try:
            cache.client.close()
        except RedisError:
            pass
    _clients.clear()
    _configured_cache.cache_clear()
