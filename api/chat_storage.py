"""Short database transactions around RAG work; ownership is checked on every lookup."""
from dataclasses import dataclass
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth_security import aware
from api.chat_format import message_view
from api.chat_schemas import DEFAULT_TITLE, MessageView, SendMessage
from api.models import Conversation, Message, new_id, utcnow


def owned_conversation(db: Session, conversation_id: str, user_id: str, *, lock=False) -> Conversation:
    statement = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    conversation = db.scalar(statement.execution_options(populate_existing=True))
    if conversation is None:
        # Same response for an unknown id and another user's id, including when caller is admin.
        raise HTTPException(404, "Không tìm thấy hội thoại")
    return conversation


def next_sequence(db: Session, conversation_id: str) -> int:
    # Writers must already hold the parent conversation's row lock.
    return db.scalar(select(func.coalesce(func.max(Message.sequence), 0)).where(
        Message.conversation_id == conversation_id,
    )) + 1


def request_message(db: Session, conversation_id: str, request_id: str, role: str) -> Message | None:
    return db.scalar(select(Message).where(
        Message.conversation_id == conversation_id, Message.request_id == request_id, Message.role == role,
    ).execution_options(populate_existing=True))


@dataclass(frozen=True)
class Generation:
    conversation_id: str
    user_id: str
    request_id: str
    token: str
    user_message_id: str


def start_generation(db: Session, user_id: str, body: SendMessage, lease_seconds: int) -> Generation | MessageView:
    conversation_id = str(body.conversationId)
    request_id = str(body.requestId) if body.requestId else new_id()
    conversation = owned_conversation(db, conversation_id, user_id, lock=True)
    question = request_message(db, conversation_id, request_id, "user")
    if question:
        if question.content != body.content or (question.details or {}).get("institutionId") != body.institutionId:
            raise HTTPException(409, "requestId đã được sử dụng cho nội dung khác")
        answer = request_message(db, conversation_id, request_id, "assistant")
        if answer:
            replay = message_view(answer)
            db.commit()
            return replay
    now = utcnow()
    if conversation.active_request_id:
        started = conversation.generation_started_at
        if started and aware(started) + timedelta(seconds=lease_seconds) > now:
            raise HTTPException(409, "Hội thoại đang xử lý một câu hỏi. Vui lòng thử lại sau.",
                                headers={"Retry-After": "5", "X-Chat-Request-Id": conversation.active_request_id})
        interrupted = request_message(db, conversation_id, conversation.active_request_id, "user")
        if interrupted and interrupted.delivery_state == "pending":
            interrupted.delivery_state = "failed"
            interrupted.details = {**(interrupted.details or {}), "errorCode": "generation_interrupted"}
    if question is None:
        sequence = next_sequence(db, conversation_id)
        question = Message(id=new_id(), conversation_id=conversation_id, role="user", content=body.content,
                           sequence=sequence, request_id=request_id, delivery_state="pending",
                           details={"institutionId": body.institutionId})
        db.add(question)
        if sequence == 1 and conversation.title == DEFAULT_TITLE:
            conversation.title = " ".join(body.content.split())[:80]
    else:
        question.delivery_state = "pending"
        question.details = {"institutionId": body.institutionId}
    token = new_id()
    conversation.active_request_id = request_id
    conversation.generation_token = token
    conversation.generation_started_at = now
    conversation.updated_at = now
    result = Generation(conversation_id, user_id, request_id, token, question.id)
    db.commit()  # The question survives LLM/network failure and no row lock spans the LLM call.
    return result


def check_generation(db: Session, generation: Generation, *, lock=False) -> Conversation:
    conversation = owned_conversation(db, generation.conversation_id, generation.user_id, lock=lock)
    if (conversation.active_request_id != generation.request_id or conversation.generation_token != generation.token):
        raise HTTPException(409, "Yêu cầu đã được thay thế bởi một lượt xử lý mới")
    return conversation


def complete_generation(db: Session, generation: Generation, payload: dict) -> MessageView:
    conversation = check_generation(db, generation, lock=True)
    question = request_message(db, generation.conversation_id, generation.request_id, "user")
    if question is None:
        raise HTTPException(404, "Không tìm thấy tin nhắn")
    answer = Message(
        id=new_id(), conversation_id=conversation.id, role="assistant", content=payload["content"],
        sequence=next_sequence(db, conversation.id), request_id=generation.request_id,
        status=payload["status"], citations=payload["citations"], delivery_state="completed",
        details={key: payload[key] for key in ("answer", "refusalReason", "institution", "latencyMs")}
                | {"replyToId": question.id},
    )
    db.add(answer)
    question.delivery_state = "completed"
    clear_generation(conversation)
    db.commit()
    return message_view(answer)


def clear_generation(conversation: Conversation):
    conversation.active_request_id = None
    conversation.generation_token = None
    conversation.generation_started_at = None
    conversation.updated_at = utcnow()


def fail_generation(db: Session, generation: Generation, error_code: str):
    db.rollback()
    # A delete or a newer attempt must never be undone by an old completion/failure callback.
    try:
        conversation = check_generation(db, generation, lock=True)
    except HTTPException:
        db.rollback()
        return
    question = request_message(db, conversation.id, generation.request_id, "user")
    if question:
        question.delivery_state = "failed"
        question.details = {**(question.details or {}), "errorCode": error_code}
    clear_generation(conversation)
    db.commit()
