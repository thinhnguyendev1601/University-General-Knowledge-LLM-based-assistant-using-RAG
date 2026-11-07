"""HTTP contract tests for api/app.py with a fake pipeline (no model loading)."""
from fastapi.testclient import TestClient

from api import app as api
from tests.test_rag import _two_school_pipe


def _client(tmp_path, reply):
    api.STATE["pipe"] = _two_school_pipe(tmp_path, reply)
    return TestClient(api.app)  # no `with` -> lifespan (real model load) is skipped


def test_chat_message_matches_frontend_contract(tmp_path):
    reply = lambda s, u: {"can_answer": True, "answer": "Dưới 3,0.",
                          "citations": [{"source": "C1", "quote": "điểm trung bình học kỳ dưới 3,0"}]}
    r = _client(tmp_path, reply).post("/api/chat/messages", json={"conversationId": "c1", "content": "Ở UIT khi nào bị cảnh báo học tập?"})
    assert r.status_code == 200
    m = r.json()
    assert {"id", "conversationId", "role", "content", "createdAt"} <= m.keys()  # types/chat.ts ChatMessage
    assert m["role"] == "assistant" and m["conversationId"] == "c1" and m["status"] == "answered"
    assert "Nguồn / Sources" in m["content"] and m["citations"][0]["docId"] == "uit-reg"
    assert m["institution"] == {"ids": ["uit"], "source": "detected"}


def test_refusal_and_bad_institution(tmp_path):
    c = _client(tmp_path, lambda s, u: {"can_answer": False, "answer": "", "citations": []})
    m = c.post("/api/chat/messages", json={"conversationId": "c1", "content": "MIT thesis rules?"}).json()
    assert m["status"] == "refused" and m["refusalReason"] == "institution_not_covered"
    r = c.post("/api/chat/messages", json={"conversationId": "c1", "content": "học phí bao nhiêu?", "institutionId": "nope"})
    assert r.status_code == 400 and "message" in r.json()


def test_institution_picker_lists_coverage(tmp_path):
    opts = {o["id"]: o for o in _client(tmp_path, None).get("/api/institutions").json()}
    assert opts["iu"]["covered"] and opts["uit"]["covered"] and not opts["mit"]["covered"]
