"""Private PostgreSQL/corpus backups. Restore only to a new quarantine database."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from api.settings import ROOT, get_settings

BACKUPS = ROOT / "var/backups"
RESTORES = ROOT / "var/restores"
NAME = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,80}\Z")
DATABASE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}\Z")
RESTORE_DATABASE = re.compile(r"university_restore_[a-z0-9_]{1,40}\Z")


def checksum(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def private_path(parent: Path, name: str):
    if not NAME.fullmatch(name):
        raise ValueError("Use a simple backup/restore name, not a path")
    if parent.is_symlink() or not parent.resolve().is_relative_to((ROOT / "var").resolve()):
        raise ValueError("Storage must stay in the private var directory")
    if not (ROOT / "var").resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Private storage must not point outside the project")
    return parent / name


def safe_files(directory: Path):
    if directory.is_symlink() or getattr(directory, "is_junction", lambda: False)():
        raise ValueError("Backup paths must not be links")
    files = []
    for path in directory.rglob("*"):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("Backup data must not contain links")
        if path.is_file():
            files.append(path)
        if len(files) > 10000:
            raise ValueError("Too many backup files")
    return sorted(files)


def remove_staging(path: Path, parent: Path):
    resolved = path.resolve()
    if (path.name.startswith("partial-") and resolved.parent == parent.resolve()
            and resolved.is_relative_to((ROOT / "var").resolve()) and not path.is_symlink()):
        shutil.rmtree(resolved)
    else:
        raise ValueError("Unsafe staging cleanup path")


class DockerPostgres:
    """Use PostgreSQL 17 tools inside the project's existing Compose service."""
    def __init__(self, database_url: str):
        self.url = make_url(database_url)
        if (self.url.get_backend_name() != "postgresql" or self.url.host not in {"127.0.0.1", "localhost"}
                or not DATABASE.fullmatch(self.url.database or "") or not DATABASE.fullmatch(self.url.username or "")):
            raise ValueError("This local Docker workflow requires a local PostgreSQL database")
        self.compose = ["docker", "compose", "-f", str(ROOT / "compose.auth.yaml")]
        result = subprocess.run([*self.compose, "port", "postgres", "5432"], capture_output=True, timeout=30)
        expected = f"127.0.0.1:{self.url.port or 5432}"
        if result.returncode or result.stdout.decode().strip() != expected:
            raise ValueError("DATABASE_URL does not match the Compose PostgreSQL port")

    def run(self, tool, arguments, *, input_file=None, output_file=None):
        result = subprocess.run([*self.compose, "exec", "-T", "postgres", tool,
                                 "--username", self.url.username, *arguments],
                                stdin=input_file, stdout=output_file or subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=300)
        if result.returncode:
            # Tool stderr can contain database content: do not print it by default.
            raise RuntimeError(f"{tool} failed with exit code {result.returncode}")
        return result

    def dump(self, destination: Path, snapshot: str):
        with destination.open("xb") as output:
            self.run("pg_dump", ["--format=custom", "--no-owner", "--no-acl",
                                 "--snapshot", snapshot, "--dbname", self.url.database], output_file=output)

    def restore(self, source: Path, target: str):
        if not RESTORE_DATABASE.fullmatch(target) or target == self.url.database:
            raise ValueError("Restore requires a new university_restore_* database")
        # createdb fails if the target exists. Never issue --clean or overwrite a database.
        self.run("createdb", [target])
        with source.open("rb") as data:
            self.run("pg_restore", ["--no-owner", "--no-acl", "--single-transaction",
                                    "--exit-on-error", "--dbname", target], input_file=data)
        engine = create_engine(self.url.set(database=target), hide_parameters=True)
        try:
            with engine.begin() as connection:
                # Restoring an old session must not resurrect a logged-out/reset credential.
                connection.execute(text("DELETE FROM sessions"))
                connection.execute(text("UPDATE account_tokens SET consumed_at=CURRENT_TIMESTAMP WHERE consumed_at IS NULL"))
        finally:
            engine.dispose()


def create_backup(name: str, settings, *, data_root=None):
    output = private_path(BACKUPS, name)
    if output.exists():
        raise ValueError("Backup already exists")
    BACKUPS.mkdir(parents=True, exist_ok=True)
    staging = BACKUPS / ("partial-" + uuid.uuid4().hex)
    staging.mkdir()
    data_root = data_root or ROOT / "data"
    try:
        if data_root.is_symlink() or getattr(data_root, "is_junction", lambda: False)():
            raise ValueError("Corpus root must not be a link")
        selected = [data_root / "manifest.csv"]
        for directory in ("processed", "index", "raw"):
            if (data_root / directory).exists():
                selected.extend(safe_files(data_root / directory))
        if not selected[0].is_file():
            raise ValueError("Corpus manifest is missing")
        originals = {}
        for source in selected:
            if source.is_symlink() or not source.resolve().is_relative_to(data_root.resolve()):
                raise ValueError("Corpus path escapes the data directory")
            relative = "data/" + source.relative_to(data_root).as_posix()
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            originals[relative] = checksum(source)
            shutil.copyfile(source, destination)
            if checksum(destination) != originals[relative]:
                raise ValueError("Corpus changed during backup")
        engine = create_engine(settings.database_url, hide_parameters=True)
        try:
            with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection, connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                snapshot = connection.scalar(text("SELECT pg_export_snapshot()"))
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                DockerPostgres(settings.database_url).dump(staging / "database.dump", snapshot)
        finally:
            engine.dispose()
        for source in selected:
            if checksum(source) != originals["data/" + source.relative_to(data_root).as_posix()]:
                raise ValueError("Corpus changed during backup; retry in a maintenance window")
        inventory = {path.relative_to(staging).as_posix(): {"sha256": checksum(path), "bytes": path.stat().st_size}
                     for path in safe_files(staging)}
        recipes = {name: checksum(ROOT / name) for name in
                   ("rag/chunker.py", "rag/retrieval.py", "rag/pipeline.py", "core/schemas.py", "requirements.txt")}
        metadata = {"formatVersion": 1, "createdAt": datetime.now(timezone.utc).isoformat(),
                    "schemaRevision": revision, "indexRevision": None, "publicationMode": "legacy_manifest",
                    "rag": {"llm": os.getenv("RAG_LLM", "ollama"), "model": os.getenv("RAG_LLM_MODEL", "llama3.2"),
                            "gate": os.getenv("RAG_GATE", "0.0"), "recipeHashes": recipes}, "files": inventory}
        (staging / "bundle.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        verify_backup(staging)
        staging.rename(output)
        return {"status": "created", "name": name, "files": len(inventory), "schemaRevision": revision}
    except Exception:
        remove_staging(staging, BACKUPS)
        raise


def verify_backup(bundle: Path):
    metadata_path = bundle / "bundle.json"
    if metadata_path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Invalid backup metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("formatVersion") != 1 or not isinstance(metadata.get("files"), dict):
        raise ValueError("Unsupported backup format")
    entries = metadata["files"]
    if not {"database.dump", "data/manifest.csv"} <= entries.keys():
        raise ValueError("Backup is incomplete")
    actual = {path.relative_to(bundle).as_posix() for path in safe_files(bundle)} - {"bundle.json"}
    if set(entries) != actual:
        raise ValueError("Backup file inventory does not match")
    for name, info in entries.items():
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
            raise ValueError("Invalid backup member path")
        target = bundle / name
        if not target.resolve().is_relative_to(bundle.resolve()):
            raise ValueError("Backup member escapes the bundle")
        if target.stat().st_size != info["bytes"] or checksum(target) != info["sha256"]:
            raise ValueError("Backup checksum mismatch")
    return metadata


def restore_backup(name: str, target: str, settings):
    bundle = private_path(BACKUPS, name)
    metadata = verify_backup(bundle)
    if not RESTORE_DATABASE.fullmatch(target):
        raise ValueError("Restore requires a university_restore_* database")
    output = private_path(RESTORES, target)
    if output.exists():
        raise ValueError("Restore data directory already exists")
    RESTORES.mkdir(parents=True, exist_ok=True)
    staging = RESTORES / ("partial-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        for name in metadata["files"]:
            if name.startswith("data/"):
                destination = staging / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(bundle / name, destination)
        DockerPostgres(settings.database_url).restore(bundle / "database.dump", target)
        staging.rename(output)
    except Exception:
        remove_staging(staging, RESTORES)
        raise
    return {"status": "restored_to_quarantine", "database": target, "schemaRevision": metadata["schemaRevision"],
            "sessionsRevoked": True, "resetTokensConsumed": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("create", "verify", "restore"))
    parser.add_argument("--name", required=True)
    parser.add_argument("--target-database")
    args = parser.parse_args()
    settings = get_settings()
    if args.operation == "create":
        result = create_backup(args.name, settings)
    elif args.operation == "verify":
        metadata = verify_backup(private_path(BACKUPS, args.name))
        result = {"status": "verified", "files": len(metadata["files"])}
    else:
        if not args.target_database:
            parser.error("restore requires --target-database")
        result = restore_backup(args.name, args.target_database, settings)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
