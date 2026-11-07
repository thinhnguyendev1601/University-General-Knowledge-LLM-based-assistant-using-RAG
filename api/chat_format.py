"""Serialize stored messages and retain the existing RAG answer/citation shape."""
from api.auth_security import aware
from api.chat_schemas import ConversationView, MessageView
from api.models import Conversation, Message
from core.schemas import AnswerResult
from rag.pipeline import DensePipeline


def conversation_view(conversation: Conversation) -> ConversationView:
    return ConversationView(id=conversation.id, title=conversation.title,
                            createdAt=aware(conversation.created_at).isoformat(),
                            updatedAt=aware(conversation.updated_at).isoformat())


def message_view(message: Message) -> MessageView:
    details = message.details or {}
    return MessageView(
        id=message.id, conversationId=message.conversation_id, role=message.role,
        content=message.content, createdAt=aware(message.created_at).isoformat(),
        sequence=message.sequence, requestId=message.request_id, deliveryStatus=message.delivery_state,
        status=message.status, citations=message.citations or [],
        institutionId=details.get("institutionId"),
        **{key: details.get(key) for key in ("answer", "refusalReason", "institution", "latencyMs", "replyToId", "errorCode")},
    )


def answer_payload(result: AnswerResult, pipe: DensePipeline) -> dict:
    by_id = {scored.chunk.chunk_id: scored.chunk for scored in result.retrieved}
    citations = []
    for citation in result.citations:
        chunk = by_id.get(citation.chunk_id)
        meta = pipe.meta.get(chunk.doc_id) if chunk else None
        citations.append({
            "chunkId": citation.chunk_id, "docId": chunk.doc_id if chunk else None,
            "title": meta.title if meta else None, "sourceUrl": meta.source_url if meta else None,
            "section": " > ".join(chunk.section_path) if chunk else "",
            "page": chunk.page_start if chunk else None, "quote": citation.quote,
        })
    content = result.answer
    if result.status != "refused" and citations:
        lines = [content, "", "Nguồn / Sources:"]
        for index, citation in enumerate(citations, 1):
            where = " — ".join(item for item in (
                citation["title"], citation["section"].split(" > ")[-1] if citation["section"] else "",
                f"tr. {citation['page']}" if citation["page"] else "",
            ) if item)
            lines.append(f"[{index}] {where}\n    “{citation['quote']}”")
        content = "\n".join(lines)
    institution = result.trace.get("institution") or {}
    return {
        "content": content, "status": result.status, "citations": citations,
        "answer": result.answer, "refusalReason": result.refusal_reason,
        "institution": {"ids": institution.get("ids", []), "source": institution.get("source")},
        "latencyMs": round(result.latency_ms or 0),
    }
