"""B1 acceptance: real SQL/auth, immutable corpus provenance and atomic audit."""
from concurrent.futures import ThreadPoolExecutor
import csv
import hashlib
import os
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.app import app
from api.models import Document, DocumentAudit, DocumentVersion, User
from api.settings import ROOT
from scripts.import_document_metadata import import_manifest
from tests.test_auth import HEADERS, PASSWORD, account, login, register

MANIFEST = ROOT / "data/manifest.csv"
BASE = "/api/admin/documents"


@pytest.fixture
def catalog(account):
    client, engine, _ = account
    with Session(engine) as db, db.begin():
        import_manifest(db, MANIFEST)
    assert register(client).status_code == 201
    with Session(engine) as db, db.begin():
        db.execute(update(User).values(role="admin"))
    auth = login(client)
    assert auth.status_code == 200
    client.headers["X-CSRF-Token"] = auth.json()["csrfToken"]
    return client, engine, client.get(BASE).json()


def counts(engine):
    with Session(engine) as db:
        return tuple(db.scalar(select(func.count()).select_from(model))
                     for model in (Document, DocumentVersion, DocumentAudit))


def corpus_hashes():
    paths = [MANIFEST, *sorted((ROOT / "data/processed").glob("*"))]
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_file()}


def write_manifest(path, rows):
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_import_is_idempotent_and_preserves_every_legacy_field(account):
    _, engine, _ = account
    before = corpus_hashes()
    with Session(engine) as db, db.begin():
        assert import_manifest(db, MANIFEST) == {"created": 21, "skipped": 0}
    with Session(engine) as db, db.begin():
        assert import_manifest(db, MANIFEST) == {"created": 0, "skipped": 21}
    assert counts(engine) == (21, 21, 21)
    with MANIFEST.open(encoding="utf-8-sig", newline="") as source:
        rows = {row["doc_id"]: row for row in csv.DictReader(source)}
    with Session(engine) as db:
        for doc in db.scalars(select(Document)):
            raw = rows[doc.legacy_doc_id]
            version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id))
            assert doc.corpus_role == raw["role"]
            assert version.manifest_metadata == raw
            assert version.version_label == raw["doc_version"]
            assert version.sha256_raw == (raw["sha256_raw"] or None)
            assert version.sha256_text == (raw["sha256_text"] or None)
            assert version.processing_status is None and version.origin == "manifest"
    assert corpus_hashes() == before


@pytest.mark.parametrize("role", ["anonymous", "user"])
def test_all_document_routes_require_admin(catalog, role):
    admin, engine, docs = catalog
    outsider = TestClient(app, headers=HEADERS)
    try:
        if role == "user":
            email = "ordinary@university.edu.vn"
            assert register(outsider, email).status_code == 201
            auth = outsider.post("/api/auth/login", json={"email": email, "password": PASSWORD})
            outsider.headers["X-CSRF-Token"] = auth.json()["csrfToken"]
        target = f"{BASE}/{docs[0]['id']}"
        expected = 401 if role == "anonymous" else 403
        for path in (BASE, target, target + "/versions"):
            assert outsider.get(path).status_code == expected
        assert outsider.patch(target, json={"title": "Unauthorized"}).status_code == expected
        assert counts(engine) == (21, 21, 21)
    finally:
        outsider.close()


def test_list_filters_literal_search_pagination_and_version_contract(catalog):
    client, _, docs = catalog
    response = client.get(BASE, params={"limit": 5})
    assert response.status_code == 200 and response.headers["X-Total-Count"] == "21"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json() == docs[:5]
    assert client.get(BASE, params={"limit": 5, "offset": 5}).json() == docs[5:10]
    assert client.get(BASE, params={"offset": 100}).json() == []
    for role, total in (("indexed", 9), ("holdout", 6), ("excluded", 6)):
        result = client.get(BASE, params={"corpusRole": role})
        assert int(result.headers["X-Total-Count"]) == total
        assert all(doc["corpusRole"] == role and doc["ragManaged"] is False for doc in result.json())
    filtered = client.get(BASE, params={"institutionId": "uit", "docType": "regulation", "docStatus": "unknown"})
    assert [doc["docId"] for doc in filtered.json()] == ["uit-acad-reg-2022"]
    assert len(client.get(BASE, params={"q": "MOET-TT08"}).json()) == 1
    assert client.get(BASE, params={"q": "%"}).json() == []
    for doc in docs:
        target = f"{BASE}/{doc['id']}"
        assert client.get(target).json() == doc
        versions = client.get(target + "/versions")
        assert versions.headers["X-Total-Count"] == "1"
        version = versions.json()[0]
        assert version["documentId"] == doc["id"] and version["processingStatus"] is None
        assert not {"manifestMetadata", "path", "storagePath"} & version.keys()
        assert client.get(target + "/versions", params={"offset": 1}).json() == []
    for suffix in ("", "/versions"):
        assert client.get(f"{BASE}/{uuid.uuid4()}{suffix}").status_code == 404
    assert client.patch(f"{BASE}/{uuid.uuid4()}", json={"title": "Missing"}).status_code == 404


def test_patch_updates_only_metadata_and_audits_with_actor(catalog):
    client, engine, docs = catalog
    doc = next(doc for doc in docs if doc["docId"] == "iu-scse-handbook-2024")
    target = f"{BASE}/{doc['id']}"
    before = corpus_hashes()
    versions_before = client.get(target + "/versions").json()
    response = client.patch(target, json={"title": "  Edited title  ", "sourceUrl": None,
                                          "effectiveDate": "2026-11", "docStatus": "unknown"})
    assert response.status_code == 200
    edited = response.json()
    assert edited["title"] == "Edited title" and edited["sourceUrl"] is None
    assert edited["corpusRole"] == doc["corpusRole"]
    assert client.get(target + "/versions").json() == versions_before
    with Session(engine) as db:
        audit = db.scalar(select(DocumentAudit).where(DocumentAudit.action == "metadata_updated"))
        assert audit.document_id == doc["id"] and audit.actor_kind == "admin"
        assert db.get(User, audit.actor_user_id).role == "admin"
        assert audit.changes["title"] == {"before": doc["title"], "after": "Edited title"}
    # No-op PATCH does not manufacture another audit/update timestamp.
    assert client.patch(target, json={"title": "Edited title"}).json() == edited
    with Session(engine) as db, db.begin():
        assert import_manifest(db, MANIFEST) == {"created": 0, "skipped": 21}
    assert client.get(target).json() == edited
    assert counts(engine) == (21, 21, 22)
    assert corpus_hashes() == before


@pytest.mark.parametrize("body", [
    {}, {"title": "   "}, {"title": None}, {"notes": None}, {"title": "x" * 1001},
    {"enabled": True}, {"corpusRole": "indexed"}, {"docId": "changed"},
    {"processingStatus": "ready"}, {"sha256Raw": "f" * 64}, {"path": "../../secret"},
    {"actorUserId": "forged"}, {"version": "new"}, {"lang": "en"},
    {"institutionId": "invalid"}, {"docStatus": "ready"}, {"sourceUrl": "file:///secret"},
    {"sourceUrl": "https://user:password@example.com/file.pdf"}, {"publicationDate": ""},
])
def test_patch_validation_rejects_unapproved_fields(catalog, body):
    client, engine, docs = catalog
    assert client.patch(f"{BASE}/{docs[0]['id']}", json=body).status_code == 422
    assert counts(engine) == (21, 21, 21)


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 101}, {"offset": -1}, {"corpusRole": "admin"},
    {"docStatus": "ready"}, {"q": " "}, {"q": "x" * 201},
])
def test_list_validation(catalog, params):
    client, _, _ = catalog
    assert client.get(BASE, params=params).status_code == 422


def test_patch_checks_csrf_and_origin(catalog):
    client, engine, docs = catalog
    target = f"{BASE}/{docs[0]['id']}"
    for headers in ({"X-CSRF-Token": "wrong"}, {"Origin": "https://evil.example"},
                    {"X-Requested-With": "invalid"}):
        assert client.patch(target, json={"title": "Rejected"}, headers=headers).status_code == 403
    del client.headers["X-CSRF-Token"]
    assert client.patch(target, json={"title": "Rejected"}).status_code == 403
    assert counts(engine) == (21, 21, 21)


def test_audit_failure_rolls_back_metadata(catalog):
    client, engine, docs = catalog

    def reject_audit(*args):
        raise SQLAlchemyError("simulated audit write failure")

    event.listen(DocumentAudit, "before_insert", reject_audit)
    try:
        response = client.patch(f"{BASE}/{docs[0]['id']}", json={"title": "Must roll back"})
        assert response.status_code == 503
    finally:
        event.remove(DocumentAudit, "before_insert", reject_audit)
    assert client.get(f"{BASE}/{docs[0]['id']}").json() == docs[0]
    assert counts(engine) == (21, 21, 21)


@pytest.mark.parametrize("change", ["duplicate", "invalid_role", "empty_role", "bad_hash", "bad_url"])
def test_import_rejects_invalid_manifest_before_writing(account, tmp_path, change):
    _, engine, _ = account
    with MANIFEST.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if change == "duplicate":
        rows.append(rows[0].copy())
    else:
        key, value = {"invalid_role": ("role", "admin"), "empty_role": ("role", ""),
                      "bad_hash": ("sha256_raw", "invalid"), "bad_url": ("source_url", "file:///secret")}[change]
        rows[-1][key] = value
    path = tmp_path / "invalid.csv"
    write_manifest(path, rows)
    with pytest.raises(ValueError), Session(engine) as db, db.begin():
        import_manifest(db, path)
    assert counts(engine) == (0, 0, 0)


def test_import_conflict_rolls_back_earlier_new_documents(catalog, tmp_path):
    _, engine, _ = catalog
    with MANIFEST.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))[:2]
    rows[0]["doc_id"] = "brand-new-doc"
    rows[1]["role"] = "excluded"
    path = tmp_path / "conflict.csv"
    write_manifest(path, rows)
    with pytest.raises(ValueError, match="Legacy metadata changed"), Session(engine) as db, db.begin():
        import_manifest(db, path)
    assert counts(engine) == (21, 21, 21)


@pytest.mark.skipif(not os.getenv("AUTH_TEST_DATABASE_URL"), reason="PostgreSQL concurrent import")
def test_concurrent_import_does_not_duplicate_documents_or_audit(account):
    _, engine, _ = account

    def run():
        with Session(engine) as db, db.begin():
            return import_manifest(db, MANIFEST)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: run(), range(2)))
    assert sum(result["created"] for result in results) == 21
    assert sum(result["skipped"] for result in results) == 21
    assert counts(engine) == (21, 21, 21)
