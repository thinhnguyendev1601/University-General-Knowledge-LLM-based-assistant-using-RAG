"""B1 contract: metadata can change; corpus membership and versions cannot."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from rag.institutions import BY_ID

CorpusRole = Literal["indexed", "holdout", "excluded"]
DocumentStatus = Literal["current", "superseded", "unknown"]


class PatchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=1000)
    publisher: str | None = Field(default=None, min_length=1, max_length=500)
    institutionId: str | None = Field(default=None, max_length=64)
    docType: str | None = Field(default=None, min_length=1, max_length=64)
    sourceUrl: HttpUrl | None = Field(default=None, max_length=4096)
    publicationDate: str | None = Field(default=None, min_length=1, max_length=64)
    effectiveDate: str | None = Field(default=None, min_length=1, max_length=64)
    docStatus: DocumentStatus | None = None
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("institutionId")
    @classmethod
    def known_institution(cls, value):
        if value is not None and value not in BY_ID:
            raise ValueError("Mã trường không hợp lệ")
        return value

    @field_validator("sourceUrl")
    @classmethod
    def no_url_credentials(cls, value):
        if value is not None and (value.username or value.password):
            raise ValueError("URL không được chứa thông tin đăng nhập")
        return value

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set:
            raise ValueError("Cần ít nhất một trường metadata")
        for field in self.model_fields_set & {"title", "publisher", "docType", "docStatus", "notes"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} không được null")
        return self


class DocumentView(BaseModel):
    id: str
    docId: str
    title: str
    publisher: str
    institutionId: str | None
    docType: str
    lang: str
    corpusRole: CorpusRole
    docStatus: DocumentStatus
    sourceUrl: str | None
    publicationDate: str | None
    effectiveDate: str | None
    versionGroup: str | None
    notes: str
    ragManaged: bool = False
    createdAt: str
    updatedAt: str


class DocumentVersionView(BaseModel):
    id: str
    documentId: str
    version: str
    origin: Literal["manifest", "upload"]
    processingStatus: Literal["uploaded", "processing", "ready", "failed"] | None
    fileFormat: str | None
    sha256Raw: str | None
    sha256Text: str | None
    nPages: int | None
    createdAt: str
