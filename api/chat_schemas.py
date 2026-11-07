from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_TITLE = "Hội thoại mới"


class CreateConversation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default=DEFAULT_TITLE, min_length=1, max_length=200)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tiêu đề không được để trống")
        return value


class RenameConversation(CreateConversation):
    title: str = Field(min_length=1, max_length=200)


class SendMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversationId: UUID
    content: str = Field(min_length=1, max_length=2000)
    institutionId: str | None = Field(default=None, min_length=1, max_length=64)
    requestId: UUID | None = None

    @field_validator("content")
    @classmethod
    def nonempty_content(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Nội dung không được để trống")
        return value


class ConversationView(BaseModel):
    id: str
    title: str
    createdAt: str
    updatedAt: str


class MessageView(BaseModel):
    id: str
    conversationId: str
    role: str
    content: str
    createdAt: str
    sequence: int
    requestId: str | None
    deliveryStatus: str
    status: str | None
    citations: list[dict]
    answer: str | None = None
    refusalReason: str | None = None
    institution: dict | None = None
    latencyMs: int | None = None
    replyToId: str | None = None
    errorCode: str | None = None
    institutionId: str | None = None
