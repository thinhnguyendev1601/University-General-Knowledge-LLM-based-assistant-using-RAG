from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import LoginSession, RateLimit, User, utcnow
from api.settings import Settings, get_settings

password_hasher = PasswordHasher()
# Missing users still perform password verification, reducing account timing disclosure.
DUMMY_PASSWORD_HASH = password_hasher.hash(secrets.token_urlsafe(32))
RATE_LIMIT_WINDOW_SECONDS = 900


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def cookie_name(settings: Settings) -> str:
    return "__Host-university_session" if settings.cookie_secure else "university_session"


def require_origin(request: Request, settings: Settings = Depends(get_settings)):
    # No cross-origin CORS is enabled: Vite/reverse proxy serves /api on the UI origin.
    if (request.headers.get("origin") != settings.origin
            or request.headers.get("x-requested-with") != "XMLHttpRequest"):
        raise HTTPException(403, "Nguồn yêu cầu không hợp lệ")


def throttle(db: Session, request: Request, action: str, email: str, email_limit: int, ip_limit: int):
    """Atomic, shared fixed-window counters, persisted even when authentication fails."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    now = int(utcnow().timestamp())
    window = RATE_LIMIT_WINDOW_SECONDS
    window_start = now // window * window
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    ip = request.client.host if request.client else "unknown"
    exceeded = False
    for scope, identity, limit in (("email", email, email_limit), ("ip", ip, ip_limit)):
        key = digest(f"{action}:{scope}:{identity}:{window_start}")
        statement = insert(RateLimit).values(key=key, window_start=window_start, count=1)
        statement = statement.on_conflict_do_update(
            index_elements=[RateLimit.key], set_={"count": RateLimit.count + 1}
        ).returning(RateLimit.count)
        exceeded = db.execute(statement).scalar_one() > limit or exceeded
    db.commit()
    if exceeded:
        raise HTTPException(429, "Bạn thao tác quá nhiều lần. Vui lòng thử lại sau.",
                            headers={"Retry-After": str(window - now % window)})


def require_user(request: Request, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> User:
    raw_token = request.cookies.get(cookie_name(settings))
    session = db.get(LoginSession, digest(raw_token)) if raw_token else None
    now = utcnow()
    if (not session or session.revoked_at or aware(session.expires_at) <= now
            or aware(session.last_seen_at) + timedelta(seconds=settings.session_idle_seconds) <= now):
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    user = db.get(User, session.user_id)
    if not user or user.status != "active":
        raise HTTPException(401, "Tài khoản không khả dụng")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        require_origin(request, settings)
        csrf = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, "Yêu cầu không hợp lệ. Vui lòng tải lại trang.")
    session.last_seen_at = now
    db.commit()
    request.state.login_session = session
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Bạn không có quyền quản trị")
    return user
