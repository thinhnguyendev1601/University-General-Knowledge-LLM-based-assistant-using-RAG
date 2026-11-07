"""Admin-only metadata APIs. B1 does not publish or reload RAG documents."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from api.auth_security import aware, require_admin
from api.database import get_db
from api.document_schemas import CorpusRole, DocumentStatus, DocumentVersionView, DocumentView, PatchDocument
from api.models import Document, DocumentAudit, DocumentVersion, User, utcnow

router = APIRouter(prefix="/api/admin/documents", tags=["Admin documents"])

PATCH_FIELDS = {
    "title": "title", "publisher": "publisher", "institutionId": "institution_id",
    "docType": "doc_type", "sourceUrl": "source_url", "publicationDate": "publication_date",
    "effectiveDate": "effective_date", "docStatus": "doc_status", "notes": "notes",
}


def document_view(doc: Document) -> DocumentView:
    return DocumentView(
        id=doc.id, docId=doc.legacy_doc_id, title=doc.title, publisher=doc.publisher,
        institutionId=doc.institution_id, docType=doc.doc_type, lang=doc.lang,
        corpusRole=doc.corpus_role, docStatus=doc.doc_status, sourceUrl=doc.source_url,
        publicationDate=doc.publication_date, effectiveDate=doc.effective_date,
        versionGroup=doc.version_group, notes=doc.notes,
        createdAt=aware(doc.created_at).isoformat(), updatedAt=aware(doc.updated_at).isoformat(),
    )


def find_document(db: Session, document_id: UUID, *, lock=False) -> Document:
    statement = select(Document).where(Document.id == str(document_id))
    if lock:
        statement = statement.with_for_update()
    doc = db.scalar(statement)
    if doc is None:
        raise HTTPException(404, "Không tìm thấy tài liệu")
    return doc


@router.get("", response_model=list[DocumentView])
def list_documents(response: Response, admin: User = Depends(require_admin), db: Session = Depends(get_db),
                   limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                   q: str | None = Query(None, min_length=1, max_length=200),
                   institutionId: str | None = Query(None, max_length=64),
                   corpusRole: CorpusRole | None = None, docStatus: DocumentStatus | None = None,
                   docType: str | None = Query(None, max_length=64)):
    filters = []
    if q is not None:
        # Treat %/_ as ordinary characters, not LIKE wildcards.
        term = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        if not term:
            raise HTTPException(422, "Từ khóa không được để trống")
        filters.append(or_(*(field.ilike(f"%{term}%", escape="\\") for field in
                             (Document.title, Document.legacy_doc_id, Document.publisher))))
    for column, value in ((Document.institution_id, institutionId), (Document.corpus_role, corpusRole),
                          (Document.doc_status, docStatus), (Document.doc_type, docType)):
        if value is not None:
            filters.append(column == value)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(Document).where(*filters)))
    docs = db.scalars(select(Document).where(*filters).order_by(Document.created_at.desc(), Document.id.desc())
                      .limit(limit).offset(offset))
    return [document_view(doc) for doc in docs]


@router.get("/{document_id}", response_model=DocumentView)
def get_document(document_id: UUID, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return document_view(find_document(db, document_id))


@router.patch("/{document_id}", response_model=DocumentView)
def patch_document(document_id: UUID, body: PatchDocument, admin: User = Depends(require_admin),
                   db: Session = Depends(get_db)):
    doc = find_document(db, document_id, lock=True)
    changes = {}
    for name, value in body.model_dump(exclude_unset=True, mode="json").items():
        attr = PATCH_FIELDS[name]
        old = getattr(doc, attr)
        if old != value:
            changes[name] = {"before": old, "after": value}
            setattr(doc, attr, value)
    if changes:
        doc.updated_at = utcnow()
        db.add(DocumentAudit(document_id=doc.id, actor_user_id=admin.id, actor_kind="admin",
                             action="metadata_updated", changes=changes))
        db.commit()  # Audit and metadata commit or roll back together.
        db.refresh(doc)
    return document_view(doc)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionView])
def list_versions(document_id: UUID, response: Response, admin: User = Depends(require_admin),
                  db: Session = Depends(get_db), limit: int = Query(50, ge=1, le=100),
                  offset: int = Query(0, ge=0)):
    doc = find_document(db, document_id)
    predicate = DocumentVersion.document_id == doc.id
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(DocumentVersion).where(predicate)))
    versions = db.scalars(select(DocumentVersion).where(predicate)
                          .order_by(DocumentVersion.created_at.desc(), DocumentVersion.id.desc()).limit(limit).offset(offset))
    return [DocumentVersionView(
        id=v.id, documentId=v.document_id, version=v.version_label, origin=v.origin,
        processingStatus=v.processing_status, fileFormat=v.file_format,
        sha256Raw=v.sha256_raw, sha256Text=v.sha256_text, nPages=v.n_pages,
        createdAt=aware(v.created_at).isoformat(),
    ) for v in versions]
