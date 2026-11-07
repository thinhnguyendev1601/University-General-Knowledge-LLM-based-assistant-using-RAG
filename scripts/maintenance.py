"""Count expired operational data; delete only with --apply. Never delete user content."""
import argparse
from datetime import timedelta
import json
from pathlib import Path
import re
import stat
import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from api.auth_security import RATE_LIMIT_WINDOW_SECONDS
from api.database import get_engine
from api.models import AccountToken, LoginSession, RateLimit, utcnow
from api.settings import ROOT, get_settings

TEMP_ROOT = ROOT / "var/tmp"
TEMP_NAME = re.compile(r"tmp-[0-9a-f]{32}\.part\Z")


def temporary_files(root: Path, now):
    """No recursion, links, arbitrary extensions or files younger than 24 hours."""
    if not root.exists():
        return []
    if root.is_symlink() or getattr(root, "is_junction", lambda: False)():
        raise ValueError("Temporary root must not be a link")
    resolved = root.resolve()
    candidates = []
    for path in root.iterdir():
        info = path.lstat()
        reparse = getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024)
        if not TEMP_NAME.fullmatch(path.name) or not stat.S_ISREG(info.st_mode) or reparse:
            continue
        if path.parent.resolve() != resolved or path.is_symlink():
            continue
        if info.st_mtime <= now.timestamp() - 86400:
            candidates.append(path)
    return candidates


def cleanup(db: Session, settings, *, apply=False, now=None):
    now = now or utcnow()
    old = now - timedelta(days=1)
    current_window = int(now.timestamp()) // RATE_LIMIT_WINDOW_SECONDS * RATE_LIMIT_WINDOW_SECONDS
    criteria = (
        ("sessions", LoginSession, or_(LoginSession.expires_at <= now,
            LoginSession.last_seen_at <= now - timedelta(seconds=settings.session_idle_seconds),
            LoginSession.revoked_at <= old)),
        ("accountTokens", AccountToken, or_(AccountToken.expires_at <= now, AccountToken.consumed_at <= old)),
        ("rateLimits", RateLimit, RateLimit.window_start < current_window),
    )
    counts = {}
    for name, model, predicate in criteria:
        if apply:
            counts[name] = db.execute(delete(model).where(predicate)).rowcount
        else:
            counts[name] = db.scalar(select(func.count()).select_from(model).where(predicate))
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    now = utcnow()
    files = temporary_files(TEMP_ROOT, now)
    with Session(get_engine()) as db, db.begin():
        counts = cleanup(db, settings, apply=args.apply, now=now)
    removed = 0
    if args.apply:
        # Revalidate candidates after the DB commit; failed unlink can be retried.
        for path in temporary_files(TEMP_ROOT, now):
            if path in files:
                path.unlink()
                removed += 1
    print(json.dumps({"operationId": str(uuid.uuid4()), "applied": args.apply, **counts,
                      "temporaryFiles": removed if args.apply else len(files)}))


if __name__ == "__main__":
    main()
