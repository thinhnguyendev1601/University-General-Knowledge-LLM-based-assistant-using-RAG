"""Domain-restricted registration, cookie sessions and email password reset."""
from datetime import timedelta
import secrets

from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth_schemas import AuthView, EmailBody, LoginBody, MessageView, RegisterBody, ResetBody, UserView
from api.auth_security import (
    DUMMY_PASSWORD_HASH, aware, cookie_name, digest, password_hasher, require_origin, require_user, throttle,
)
from api.database import get_db
from api.mail import SMTPMailer, get_mailer
from api.models import AccountToken, LoginSession, User, utcnow
from api.settings import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
REGISTRATION_MESSAGE = "Đăng ký thành công. Bạn có thể đăng nhập ngay."
RESET_MESSAGE = "Nếu tài khoản đủ điều kiện, liên kết đặt lại mật khẩu đã được gửi."


def auth_view(user: User, session: LoginSession) -> AuthView:
    return AuthView(user=UserView.model_validate(user), csrfToken=session.csrf_token,
                    expiresAt=aware(session.expires_at).isoformat())


def issue_reset_token(db: Session, user: User, settings: Settings, mailer: SMTPMailer):
    now = utcnow()
    raw = secrets.token_urlsafe(32)
    db.execute(update(AccountToken).where(
        AccountToken.user_id == user.id, AccountToken.purpose == "reset", AccountToken.consumed_at.is_(None),
    ).values(consumed_at=now))
    db.add(AccountToken(user_id=user.id, token_hash=digest(raw), purpose="reset",
                        expires_at=now + timedelta(seconds=settings.reset_seconds)))
    db.flush()
    # SMTP failure rolls back the new reset token, keeping any old token valid.
    mailer.send_password_reset(user.email, raw)
    db.commit()


def consume_reset_token(db: Session, raw: str) -> User:
    now = utcnow()
    # Serialize reset requests and login/password changes on the same user.
    user_id = db.scalar(select(AccountToken.user_id).where(
        AccountToken.token_hash == digest(raw), AccountToken.purpose == "reset",
    ))
    user = db.scalar(select(User).where(User.id == user_id).with_for_update()) if user_id else None
    consumed = db.execute(update(AccountToken).where(
        AccountToken.token_hash == digest(raw), AccountToken.purpose == "reset",
        AccountToken.consumed_at.is_(None), AccountToken.expires_at > now,
    ).values(consumed_at=now).returning(AccountToken.id)).scalar_one_or_none()
    if not user or not consumed or user.status != "active":
        db.rollback()
        raise HTTPException(400, "Liên kết không hợp lệ, đã được sử dụng hoặc đã hết hạn.")
    return user


@router.post("/register", status_code=201, response_model=MessageView, dependencies=[Depends(require_origin)])
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)):
    throttle(db, request, "register", body.email, email_limit=3, ip_limit=20)
    password_hash = password_hasher.hash(body.password.get_secret_value())
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise HTTPException(409, "Email này đã được đăng ký. Vui lòng đăng nhập.")
    user = User(email=body.email, name=body.name, password_hash=password_hash, role="user", status="active")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # Concurrent requests are also protected by the unique constraint.
        raise HTTPException(409, "Email này đã được đăng ký. Vui lòng đăng nhập.")
    return MessageView(message=REGISTRATION_MESSAGE)


@router.post("/login", response_model=AuthView, dependencies=[Depends(require_origin)])
def login(body: LoginBody, request: Request, response: Response, db: Session = Depends(get_db),
          settings: Settings = Depends(get_settings)):
    throttle(db, request, "login", body.email, email_limit=10, ip_limit=50)
    user = db.scalar(select(User).where(User.email == body.email).with_for_update())
    try:
        password_hasher.verify(user.password_hash if user else DUMMY_PASSWORD_HASH, body.password.get_secret_value())
    except (VerificationError, InvalidHashError):
        raise HTTPException(401, "Email hoặc mật khẩu không đúng")
    if not user or user.status != "active":
        raise HTTPException(401, "Không thể đăng nhập. Tài khoản không khả dụng.")
    if password_hasher.check_needs_rehash(user.password_hash):
        user.password_hash = password_hasher.hash(body.password.get_secret_value())
    now = utcnow()
    old_cookie = request.cookies.get(cookie_name(settings))
    if old_cookie:
        db.execute(update(LoginSession).where(LoginSession.id == digest(old_cookie)).values(revoked_at=now))
    raw = secrets.token_urlsafe(32)
    session = LoginSession(id=digest(raw), user_id=user.id, csrf_token=secrets.token_urlsafe(32),
                           expires_at=now + timedelta(seconds=settings.session_seconds))
    db.add(session)
    db.commit()
    response.set_cookie(cookie_name(settings), raw, max_age=settings.session_seconds,
                        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/")
    return auth_view(user, session)


@router.get("/me", response_model=AuthView)
def me(request: Request, user: User = Depends(require_user)):
    return auth_view(user, request.state.login_session)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, user: User = Depends(require_user),
           db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    request.state.login_session.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(cookie_name(settings), path="/", secure=settings.cookie_secure,
                           httponly=True, samesite="lax")


@router.post("/forgot-password", status_code=202, response_model=MessageView, dependencies=[Depends(require_origin)])
def forgot_password(body: EmailBody, request: Request, db: Session = Depends(get_db),
                    settings: Settings = Depends(get_settings), mailer: SMTPMailer = Depends(get_mailer)):
    throttle(db, request, "forgot", body.email, email_limit=3, ip_limit=20)
    user = db.scalar(select(User).where(User.email == body.email).with_for_update())
    if user and user.status == "active":
        issue_reset_token(db, user, settings, mailer)
    return MessageView(message=RESET_MESSAGE)


@router.post("/reset-password", response_model=MessageView, dependencies=[Depends(require_origin)])
def reset_password(body: ResetBody, request: Request, db: Session = Depends(get_db)):
    throttle(db, request, "reset", "all", email_limit=200, ip_limit=30)
    user = consume_reset_token(db, body.token.get_secret_value())
    user.password_hash = password_hasher.hash(body.password.get_secret_value())
    now = utcnow()
    db.execute(update(LoginSession).where(LoginSession.user_id == user.id).values(revoked_at=now))
    db.execute(update(AccountToken).where(
        AccountToken.user_id == user.id, AccountToken.purpose == "reset", AccountToken.consumed_at.is_(None),
    ).values(consumed_at=now))
    db.commit()
    return MessageView(message="Mật khẩu đã được thay đổi. Vui lòng đăng nhập lại.")
