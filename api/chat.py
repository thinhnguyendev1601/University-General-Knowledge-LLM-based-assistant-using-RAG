"""Private conversation APIs. No client-supplied owner ids or admin ownership bypass."""
import logging
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.auth_security import require_user
from api.chat_format import answer_payload, conversation_view, message_view
from api.chat_schemas import ConversationView, CreateConversation, MessageView, RenameConversation, SendMessage
from api.chat_storage import (
    complete_generation, fail_generation, owned_conversation, start_generation,
)
from api.database import get_db
from api.models import Conversation, Message, User, utcnow
from api.rag_runtime import get_pipeline
from api.rag_admission import RagAdmission, RagBusy, RagTimedOut, get_admission
from api.settings import Settings, get_settings

router = APIRouter(prefix="/api/chat", tags=["Conversations"])
logger = logging.getLogger("uvicorn.error")


@router.get("/config")
def chat_config(user: User = Depends(require_user), settings: Settings = Depends(get_settings)):
    return {"requestTimeoutMs": int((settings.chat_queue_timeout_seconds + settings.chat_processing_timeout_seconds + 30) * 1000),
            "recoveryAfterSeconds": settings.chat_generation_lease_seconds}


@router.post("/conversations", status_code=201, response_model=ConversationView)
def create_conversation(body: CreateConversation, user: User = Depends(require_user), db: Session = Depends(get_db)):
    conversation = Conversation(user_id=user.id, title=body.title)
    db.add(conversation)
    db.commit()
    return conversation_view(conversation)


@router.get("/conversations", response_model=list[ConversationView])
def list_conversations(response: Response, limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0),
                       user: User = Depends(require_user), db: Session = Depends(get_db)):
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(Conversation).where(
        Conversation.user_id == user.id,
    )))
    conversations = db.scalars(select(Conversation).where(Conversation.user_id == user.id).order_by(
        Conversation.updated_at.desc(), Conversation.id.desc(),
    ).limit(limit).offset(offset))
    return [conversation_view(conversation) for conversation in conversations]


@router.get("/conversations/{conversation_id}", response_model=ConversationView)
def get_conversation(conversation_id: UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return conversation_view(owned_conversation(db, str(conversation_id), user.id))


@router.patch("/conversations/{conversation_id}", response_model=ConversationView)
def rename_conversation(conversation_id: UUID, body: RenameConversation,
                        user: User = Depends(require_user), db: Session = Depends(get_db)):
    conversation = owned_conversation(db, str(conversation_id), user.id, lock=True)
    conversation.title = body.title
    conversation.updated_at = utcnow()
    db.commit()
    return conversation_view(conversation)


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    conversation = owned_conversation(db, str(conversation_id), user.id, lock=True)
    db.execute(delete(Message).where(Message.conversation_id == conversation.id))
    db.delete(conversation)
    db.commit()


@router.delete("/conversations", status_code=204)
def delete_all_conversations(user: User = Depends(require_user), db: Session = Depends(get_db)):
    # Stable lock order avoids deadlocks; conversations created after this snapshot remain intact.
    ids = list(db.scalars(select(Conversation.id).where(Conversation.user_id == user.id).order_by(
        Conversation.id,
    ).with_for_update()))
    for start in range(0, len(ids), 500):
        batch = ids[start:start + 500]
        db.execute(delete(Message).where(Message.conversation_id.in_(batch)))
        db.execute(delete(Conversation).where(Conversation.id.in_(batch), Conversation.user_id == user.id))
    db.commit()


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageView])
def list_messages(conversation_id: UUID, response: Response, limit: int = Query(100, ge=1, le=500),
                  afterSequence: int = Query(0, ge=0), user: User = Depends(require_user), db: Session = Depends(get_db)):
    conversation = owned_conversation(db, str(conversation_id), user.id)
    response.headers["X-Total-Count"] = str(db.scalar(select(func.count()).select_from(Message).where(
        Message.conversation_id == conversation.id,
    )))
    messages = db.scalars(select(Message).where(
        Message.conversation_id == conversation.id, Message.sequence > afterSequence,
    ).order_by(Message.sequence).limit(limit))
    return [message_view(message) for message in messages]


@router.post("/messages", response_model=MessageView)
def send_message(body: SendMessage, response: Response, user: User = Depends(require_user),
                 db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                 admission: RagAdmission = Depends(get_admission)):
    # Check ownership before consulting the model or persisting any client data.
    user_id = user.id
    owned_conversation(db, str(body.conversationId), user_id)
    started = time.monotonic()
    timings = {}
    database_started = time.monotonic()
    generation = start_generation(db, user_id, body, settings.chat_generation_lease_seconds)
    timings["databaseMs"] = (time.monotonic() - database_started) * 1000
    if isinstance(generation, MessageView):
        response.headers["X-Chat-Request-Id"] = generation.requestId or ""
        return generation
    response.headers["X-Chat-Request-Id"] = generation.request_id
    outcome = "failed"
    try:
        pipe = get_pipeline()
        db.commit()  # Release the ownership read transaction before waiting for RAG.
        result = admission.run(lambda: pipe.answer(body.content, institution=body.institutionId),
                               max_waiting=settings.chat_max_waiting,
                               queue_timeout=settings.chat_queue_timeout_seconds,
                               processing_timeout=settings.chat_processing_timeout_seconds, timings=timings)
        database_started = time.monotonic()
        saved = complete_generation(db, generation, answer_payload(result, pipe))
        timings["databaseMs"] += (time.monotonic() - database_started) * 1000
        response.headers["Server-Timing"] = ", ".join(
            f"{name.removesuffix('Ms')};dur={value:.2f}" for name, value in timings.items())
        outcome = "completed"
        return saved
    except (RagBusy, RagTimedOut) as error:
        code = "rag_busy" if isinstance(error, RagBusy) else "rag_timeout"
        outcome = code
        fail_generation(db, generation, code)
        raise HTTPException(503 if isinstance(error, RagBusy) else 504,
                            "Hệ thống đang bận. Vui lòng thử lại sau." if isinstance(error, RagBusy)
                            else "Quá thời gian trả lời. Bạn có thể thử lại câu hỏi này.",
                            headers={"Retry-After": "5", "X-Chat-Request-Id": generation.request_id})
    except HTTPException as error:
        fail_generation(db, generation, "generation_unavailable")
        error.headers = {**(error.headers or {}), "X-Chat-Request-Id": generation.request_id}
        raise
    except ValueError:
        fail_generation(db, generation, "invalid_institution")
        raise HTTPException(400, "Trường hoặc dữ liệu câu hỏi không hợp lệ", headers={"X-Chat-Request-Id": generation.request_id})
    except RuntimeError:
        fail_generation(db, generation, "llm_unavailable")
        raise HTTPException(503, "Dịch vụ trả lời tạm thời không khả dụng. Vui lòng thử lại.",
                            headers={"X-Chat-Request-Id": generation.request_id})
    except SQLAlchemyError:
        db.rollback()
        raise
    except Exception as error:
        logger.error("Chat generation failed: request=%s error_type=%s", generation.request_id, type(error).__name__)
        fail_generation(db, generation, "generation_failed")
        raise HTTPException(500, "Không thể tạo câu trả lời. Vui lòng thử lại.",
                            headers={"X-Chat-Request-Id": generation.request_id})
    finally:
        logger.info("chat request_id=%s outcome=%s total_ms=%.2f queue_ms=%.2f retrieval_ms=%.2f generation_ms=%.2f database_ms=%.2f",
                    generation.request_id, outcome, (time.monotonic() - started) * 1000,
                    timings.get("queueMs", 0), timings.get("retrievalMs", 0),
                    timings.get("generationMs", 0), timings.get("databaseMs", 0))
