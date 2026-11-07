"""Bootstrap B1 metadata without changing corpus files or the running RAG index.

Run from the project root: python -m scripts.import_document_metadata
"""
import argparse
import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from api.database import get_engine
from api.document_schemas import PatchDocument
from api.models import Document, DocumentAudit, DocumentVersion, new_id, utcnow
from api.settings import ROOT
from core.schemas import DocumentMeta
from rag.institutions import institution_of_doc


def read_manifest(path: Path) -> list[tuple[DocumentMeta, dict]]:
    rows = []
    seen = set()
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        required = {"doc_id", "doc_version", "title", "publisher", "doc_type", "lang", "role"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Manifest is missing required columns")
        for number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Manifest row {number}: malformed CSV")
            raw = dict(row)  # Immutable provenance, including fields outside the API contract.
            data = {k: v.strip() for k, v in row.items() if k in DocumentMeta.model_fields and v.strip()}
            if not required <= data.keys():
                raise ValueError(f"Manifest row {number}: required metadata is empty")
            meta = DocumentMeta.model_validate(data)
            if meta.doc_id in seen:
                raise ValueError(f"Manifest row {number}: duplicate doc_id {meta.doc_id}")
            seen.add(meta.doc_id)
            # Apply the same editable-field limits as the API before any database write.
            PatchDocument(title=meta.title, publisher=meta.publisher, docType=meta.doc_type,
                          sourceUrl=meta.source_url, publicationDate=meta.publication_date,
                          effectiveDate=meta.effective_date, docStatus=meta.doc_status, notes=meta.notes)
            for value, maximum in ((meta.doc_id, 200), (meta.doc_version, 128),
                                   (meta.version_group, 200), (meta.file_format, 16)):
                if value is not None and len(value) > maximum:
                    raise ValueError(f"Manifest row {number}: metadata exceeds storage limits")
            for value in (meta.sha256_raw, meta.sha256_text):
                if value is not None and (len(value) != 64 or any(c not in "0123456789abcdef" for c in value)):
                    raise ValueError(f"Manifest row {number}: invalid SHA-256")
            if meta.n_pages is not None and meta.n_pages < 1:
                raise ValueError(f"Manifest row {number}: n_pages must be positive")
            rows.append((meta, raw))
    return rows


def import_manifest(db: Session, path: Path) -> dict[str, int]:
    """Caller owns the transaction. Existing rows never overwrite admin edits.

    A changed legacy row/version is rejected: import is a bootstrap operation,
    not a second independently editable source or a publication mechanism.
    """
    rows = read_manifest(path)
    insert = sqlite_insert if db.get_bind().dialect.name == "sqlite" else pg_insert
    created = 0
    for meta, raw in rows:
        doc_id = new_id()
        now = utcnow()
        statement = insert(Document).values(
            id=doc_id, legacy_doc_id=meta.doc_id, title=meta.title, publisher=meta.publisher,
            institution_id=institution_of_doc(meta.doc_id), doc_type=meta.doc_type,
            lang=meta.lang, corpus_role=meta.role, doc_status=meta.doc_status,
            source_url=meta.source_url, publication_date=meta.publication_date,
            effective_date=meta.effective_date, version_group=meta.version_group,
            notes=meta.notes, created_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[Document.legacy_doc_id]).returning(Document.id)
        inserted = db.execute(statement).scalar_one_or_none()
        if inserted is None:
            existing = db.scalar(select(Document).where(Document.legacy_doc_id == meta.doc_id))
            version = db.scalar(select(DocumentVersion).where(
                DocumentVersion.document_id == existing.id, DocumentVersion.origin == "manifest",
                DocumentVersion.version_label == meta.doc_version,
            ))
            if (existing.corpus_role != meta.role or version is None
                    or version.version_label != meta.doc_version or version.manifest_metadata != raw):
                raise ValueError(f"Legacy metadata changed for {meta.doc_id}; use a reviewed version workflow")
            continue
        db.add(DocumentVersion(document_id=doc_id, version_label=meta.doc_version, origin="manifest",
                               processing_status=None, file_format=meta.file_format, n_pages=meta.n_pages,
                               sha256_raw=meta.sha256_raw, sha256_text=meta.sha256_text, manifest_metadata=raw))
        db.add(DocumentAudit(document_id=doc_id, actor_kind="manifest_import", action="metadata_imported",
                             changes={"docId": meta.doc_id, "version": meta.doc_version, "corpusRole": meta.role}))
        # Flush each document's children before another importer can observe its conflict.
        db.flush()
        created += 1
    return {"created": created, "skipped": len(rows) - created}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/manifest.csv")
    args = parser.parse_args()
    with Session(get_engine()) as db, db.begin():
        result = import_manifest(db, args.manifest)
    print(f"Created {result['created']} documents; skipped {result['skipped']} unchanged documents.")


if __name__ == "__main__":
    main()
