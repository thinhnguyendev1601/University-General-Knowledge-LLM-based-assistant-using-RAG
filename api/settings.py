"""Environment-based configuration. Secrets stay in the ignored .env file."""
from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql+psycopg://university:local-development-only@127.0.0.1:55432/university"
    frontend_url: str = "http://localhost:5173"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    mail_from: str = "no-reply@university.edu.vn"
    cookie_secure: bool = False
    session_seconds: int = 28800
    session_idle_seconds: int = 1800
    reset_seconds: int = 900
    rag_enabled: bool = True
    chat_generation_lease_seconds: int = 900
    app_env: str = "development"
    chat_max_waiting: int = 2
    chat_queue_timeout_seconds: float = 10
    chat_processing_timeout_seconds: float = 180

    def __post_init__(self):
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production")
        parsed = urlsplit(self.frontend_url)
        if (parsed.scheme not in {"http", "https"} or not parsed.netloc
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("FRONTEND_URL must be an HTTP(S) origin, without a path or credentials")
        if parsed.scheme == "https" and not self.cookie_secure:
            raise ValueError("HTTPS deployments require COOKIE_SECURE=true")
        if self.app_env == "production":
            if parsed.scheme != "https" or not self.cookie_secure:
                raise ValueError("Production requires HTTPS and COOKIE_SECURE=true")
            if "local-development-only" in self.database_url:
                raise ValueError("Production requires dedicated database credentials")
        if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "[::1]", "::1"}:
            raise ValueError("Non-local deployments require HTTPS")
        if self.smtp_username and not self.smtp_starttls:
            raise ValueError("Authenticated SMTP requires SMTP_STARTTLS=true")
        if min(self.session_seconds, self.session_idle_seconds, self.reset_seconds, self.chat_generation_lease_seconds) <= 0:
            raise ValueError("Token and session lifetimes must be positive")
        import math
        if (self.chat_max_waiting < 0 or self.chat_max_waiting > 32
                or not all(math.isfinite(v) and v > 0 for v in
                           (self.chat_queue_timeout_seconds, self.chat_processing_timeout_seconds))):
            raise ValueError("Chat queue limits and timeouts are invalid")
        if self.chat_generation_lease_seconds <= self.chat_queue_timeout_seconds + self.chat_processing_timeout_seconds + 30:
            raise ValueError("Chat lease must exceed queue + processing timeout by more than 30 seconds")

    @property
    def origin(self) -> str:
        return self.frontend_url.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.database_url),
        frontend_url=os.getenv("FRONTEND_URL", Settings.frontend_url),
        smtp_host=os.getenv("SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("SMTP_PORT", "1025")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_starttls=os.getenv("SMTP_STARTTLS", "false").lower() == "true",
        mail_from=os.getenv("MAIL_FROM", "no-reply@university.edu.vn"),
        cookie_secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        session_seconds=int(os.getenv("SESSION_SECONDS", "28800")),
        session_idle_seconds=int(os.getenv("SESSION_IDLE_SECONDS", "1800")),
        reset_seconds=int(os.getenv("RESET_SECONDS", "900")),
        rag_enabled=os.getenv("RAG_ENABLED", "true").lower() == "true",
        chat_generation_lease_seconds=int(os.getenv("CHAT_GENERATION_LEASE_SECONDS", "900")),
        app_env=os.getenv("APP_ENV", "development"),
        chat_max_waiting=int(os.getenv("CHAT_MAX_WAITING", "2")),
        chat_queue_timeout_seconds=float(os.getenv("CHAT_QUEUE_TIMEOUT_SECONDS", "10")),
        chat_processing_timeout_seconds=float(os.getenv("CHAT_PROCESSING_TIMEOUT_SECONDS", "180")),
    )
