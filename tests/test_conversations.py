"""Real cookie/CSRF/SQL ownership tests; the model is replaced by a tiny deterministic pipeline."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import os
from threading import Event
from types import SimpleNamespace
import uuid

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app import app
from api.chat_format import answer_payload
from api.chat_schemas import SendMessage
from api.chat_storage import complete_generation, start_generation
from api.models import Conversation, Message, User, utcnow
from api.rag_runtime import STATE
from tests.test_auth import HEADERS, PASSWORD, account
from tests.test_rag import _two_school_pipe

QUESTION = "Ở UIT khi nào bị cảnh báo học tập?"


@pytest.fixture
def history(account, tmp_path):
    alice, engine, _ = account
    clients = [alice]

    def sign_in(email, *, role="user", client=None):
        client = client or TestClient(app, headers=HEADERS)
        if client not in clients:
            clients.append(client)
        assert client.post("/api/auth/register", json={"name": email.split("@")[0], "email": email, "password": PASSWORD}).status_code == 201
        if role == "admin":
            with Session(engine) as db:
                db.scalar(select(User).where(User.email == email)).role = role
                db.commit()
        response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200
        client.headers["X-CSRF-Token"] = response.json()["csrfToken"]
        return client

    sign_in("alice@university.edu.vn", client=alice)
    bob = sign_in("bob@university.edu.vn")
    pipe = _two_school_pipe(tmp_path, lambda system, prompt: {
        "can_answer": True, "answer": "Dưới 3,0.",
        "citations": [{"source": "C1", "quote": "điểm trung bình học kỳ dưới 3,0"}],
    })
    answer = pipe.answer
    calls = []

    def traced_answer(question, institution=None):
        calls.append((question, institution))
        return answer(question, institution=institution)

    pipe.answer = traced_answer
    old_pipe = STATE.get("pipe")
    STATE["pipe"] = pipe
    try:
        yield SimpleNamespace(alice=alice, bob=bob, engine=engine, pipe=pipe, calls=calls, sign_in=sign_in)
    finally:
        for client in clients[1:]:
            client.close()
        if old_pipe is None:
            STATE.pop("pipe", None)
        else:
            STATE["pipe"] = old_pipe


def create(client, **body):
    response = client.post("/api/chat/conversations", json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def send(client, conversation_id, **fields):
    return client.post("/api/chat/messages", json={"conversationId": conversation_id, "content": QUESTION, **fields})


def test_create_list_get_rename_and_pagination_are_private(history):
    alice, bob = history.alice, history.bob
    first = create(alice)
    second = create(alice, title="Custom title")
    other = create(bob)
    response = alice.get("/api/chat/conversations", params={"limit": 1})
    assert response.status_code == 200 and response.headers["X-Total-Count"] == "2"
    assert response.json()[0]["id"] == second
    assert alice.get("/api/chat/conversations", params={"limit": 1, "offset": 1}).json()[0]["id"] == first
    assert bob.get("/api/chat/conversations").json()[0]["id"] == other
    renamed = alice.patch(f"/api/chat/conversations/{first}", json={"title": "  Renamed  "})
    assert renamed.status_code == 200 and renamed.json()["title"] == "Renamed"
    assert alice.get(f"/api/chat/conversations/{first}").json() == renamed.json()
    assert "userId" not in renamed.json()
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("caller_role", ["user", "admin"])
def test_foreign_and_unknown_ids_have_same_404_for_every_operation(history, caller_role):
    owner = history.alice
    intruder = history.bob if caller_role == "user" else history.sign_in("admin@university.edu.vn", role="admin")
    conversation_id = create(owner)
    unknown = str(uuid.uuid4())
    for target in [conversation_id, unknown]:
        assert intruder.get(f"/api/chat/conversations/{target}").status_code == 404
        assert intruder.get(f"/api/chat/conversations/{target}/messages").status_code == 404
        assert intruder.patch(f"/api/chat/conversations/{target}", json={"title": "stolen"}).status_code == 404
        assert intruder.delete(f"/api/chat/conversations/{target}").status_code == 404
        assert send(intruder, target).status_code == 404
    assert history.calls == []
    with Session(history.engine) as db:
        assert db.scalar(select(func.count()).select_from(Message)) == 0
        assert db.get(Conversation, conversation_id).title == "Hội thoại mới"


def test_chat_roundtrip_preserves_questions_answers_citations_and_order(history):
    client = history.alice
    conversation_id = create(client)
    request_id = str(uuid.uuid4())
    response = send(client, conversation_id, requestId=request_id)
    assert response.status_code == 200
    answer = response.json()
    assert answer["status"] == "answered" and answer["deliveryStatus"] == "completed"
    assert answer["requestId"] == request_id and response.headers["X-Chat-Request-Id"] == request_id
    assert answer["citations"][0]["docId"] == "uit-reg" and "Nguồn / Sources" in answer["content"]
    messages = client.get(f"/api/chat/conversations/{conversation_id}/messages").json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [message["sequence"] for message in messages] == [1, 2]
    assert messages[0]["content"] == QUESTION and messages[1] == answer
    assert answer["replyToId"] == messages[0]["id"]
    assert client.get(f"/api/chat/conversations/{conversation_id}").json()["title"] == QUESTION
    assert send(client, conversation_id).status_code == 200
    page = client.get(f"/api/chat/conversations/{conversation_id}/messages", params={"afterSequence": 2, "limit": 1})
    assert page.json()[0]["sequence"] == 3 and page.headers["X-Total-Count"] == "4"


def test_history_survives_logout_and_a_new_login_session(history):
    client = history.alice
    conversation_id = create(client, title="Keep this title")
    assert send(client, conversation_id).status_code == 200
    before = client.get(f"/api/chat/conversations/{conversation_id}/messages").json()
    assert client.post("/api/auth/logout", json={}).status_code == 204
    assert client.get("/api/chat/conversations").status_code == 401
    response = client.post("/api/auth/login", json={"email": "alice@university.edu.vn", "password": PASSWORD})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrfToken"]
    assert client.get(f"/api/chat/conversations/{conversation_id}/messages").json() == before
    assert client.get(f"/api/chat/conversations/{conversation_id}").json()["title"] == "Keep this title"


def test_request_id_replays_saved_answer_and_rejects_different_content(history):
    conversation_id = create(history.alice)
    request_id = str(uuid.uuid4())
    first = send(history.alice, conversation_id, requestId=request_id)
    replay = send(history.alice, conversation_id, requestId=request_id)
    assert first.status_code == 200 and replay.json() == first.json()
    assert len(history.calls) == 1
    assert send(history.alice, conversation_id, requestId=request_id, content="Different question").status_code == 409
    assert send(history.alice, conversation_id, requestId=request_id, institutionId="iu").status_code == 409
    assert len(history.alice.get(f"/api/chat/conversations/{conversation_id}/messages").json()) == 2


def test_model_failure_keeps_question_and_retry_does_not_duplicate_it(history):
    conversation_id = create(history.alice)
    request_id = str(uuid.uuid4())
    working_answer = history.pipe.answer

    def fail(*args, **kwargs):
        raise RuntimeError("private provider error that must not be exposed")

    history.pipe.answer = fail
    failure = send(history.alice, conversation_id, requestId=request_id)
    assert failure.status_code == 503 and "private provider error" not in failure.text
    assert failure.headers["X-Chat-Request-Id"] == request_id
    saved = history.alice.get(f"/api/chat/conversations/{conversation_id}/messages").json()
    assert len(saved) == 1 and saved[0]["deliveryStatus"] == "failed"
    assert saved[0]["errorCode"] == "llm_unavailable"
    history.pipe.answer = working_answer
    assert send(history.alice, conversation_id, requestId=request_id).status_code == 200
    retried = history.alice.get(f"/api/chat/conversations/{conversation_id}/messages").json()
    assert len(retried) == 2 and retried[0]["id"] == saved[0]["id"]
    assert retried[0]["deliveryStatus"] == "completed" and retried[0]["errorCode"] is None


def test_rag_disabled_still_allows_history_and_failed_question_recovery(history):
    conversation_id = create(history.alice)
    STATE.pop("pipe")
    response = send(history.alice, conversation_id)
    assert response.status_code == 503 and "X-Chat-Request-Id" in response.headers
    assert history.alice.get("/api/chat/conversations").status_code == 200
    assert history.alice.get(f"/api/chat/conversations/{conversation_id}/messages").json()[0]["deliveryStatus"] == "failed"


def test_delete_conversation_removes_messages_without_touching_another_user(history):
    own = create(history.alice)
    other = create(history.bob)
    send(history.alice, own)
    send(history.bob, other)
    assert history.alice.delete(f"/api/chat/conversations/{own}").status_code == 204
    assert history.alice.get(f"/api/chat/conversations/{own}/messages").status_code == 404
    assert len(history.bob.get(f"/api/chat/conversations/{other}/messages").json()) == 2
    with Session(history.engine) as db:
        assert db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == own)) == 0


def test_delete_all_only_deletes_current_users_snapshot(history):
    first, second = create(history.alice), create(history.alice)
    other = create(history.bob)
    send(history.alice, first)
    send(history.alice, second)
    send(history.bob, other)
    assert history.alice.delete("/api/chat/conversations").status_code == 204
    assert history.alice.get("/api/chat/conversations").json() == []
    assert len(history.bob.get(f"/api/chat/conversations/{other}/messages").json()) == 2


def test_deleting_during_generation_does_not_resurrect_the_conversation(history):
    conversation_id = create(history.alice)
    original_answer = history.pipe.answer
    other_tab = TestClient(app, headers=history.alice.headers)
    other_tab.cookies.update(history.alice.cookies)

    def delete_then_answer(*args, **kwargs):
        assert other_tab.delete(f"/api/chat/conversations/{conversation_id}").status_code == 204
        return original_answer(*args, **kwargs)

    history.pipe.answer = delete_then_answer
    try:
        assert send(history.alice, conversation_id).status_code == 404
    finally:
        other_tab.close()
    with Session(history.engine) as db:
        assert db.get(Conversation, conversation_id) is None
        assert db.scalar(select(func.count()).select_from(Message)) == 0


def test_input_validation_rejects_owner_role_and_forged_answer_fields(history):
    client = history.alice
    assert client.post("/api/chat/conversations", json={"title": "x", "userId": "another-user"}).status_code == 422
    assert client.post("/api/chat/conversations", json={"title": "  "}).status_code == 422
    conversation_id = create(client)
    assert client.patch(f"/api/chat/conversations/{conversation_id}", json={"userId": "another-user", "title": "x"}).status_code == 422
    for fields in [{"content": "  "}, {"content": "x" * 2001}, {"role": "assistant"}, {"citations": []}, {"userId": "someone"}]:
        assert send(client, conversation_id, **fields).status_code == 422
    assert send(client, str(uuid.uuid4())).status_code == 404
    assert client.get("/api/chat/conversations", params={"limit": 101}).status_code == 422
    assert client.get(f"/api/chat/conversations/{conversation_id}/messages", params={"afterSequence": -1}).status_code == 422
    assert not history.calls


def test_all_mutations_require_csrf_and_all_routes_require_login(history):
    conversation_id = create(history.alice)
    operations = [
        ("GET", "/api/chat/conversations", None),
        ("POST", "/api/chat/conversations", {}),
        ("GET", f"/api/chat/conversations/{conversation_id}", None),
        ("PATCH", f"/api/chat/conversations/{conversation_id}", {"title": "x"}),
        ("DELETE", f"/api/chat/conversations/{conversation_id}", None),
        ("DELETE", "/api/chat/conversations", None),
        ("GET", f"/api/chat/conversations/{conversation_id}/messages", None),
        ("POST", "/api/chat/messages", {"conversationId": conversation_id, "content": QUESTION}),
    ]
    anonymous = TestClient(app, headers=HEADERS)
    try:
        for method, path, body in operations:
            assert anonymous.request(method, path, json=body).status_code == 401
        no_csrf = TestClient(app, headers=HEADERS)
        no_csrf.cookies.update(history.alice.cookies)
        try:
            for method, path, body in operations:
                if method != "GET":
                    assert no_csrf.request(method, path, json=body).status_code == 403
            assert no_csrf.get("/api/chat/conversations").status_code == 200
        finally:
            no_csrf.close()
    finally:
        anonymous.close()


def test_interrupted_request_can_retry_after_lease_and_old_worker_cannot_overwrite(history):
    conversation_id = create(history.alice)
    request_id = str(uuid.uuid4())
    body = SendMessage(conversationId=conversation_id, content=QUESTION, requestId=request_id)
    with Session(history.engine) as db:
        user_id = db.get(Conversation, conversation_id).user_id
        old = start_generation(db, user_id, body, 900)
    assert send(history.alice, conversation_id, requestId=request_id).status_code == 409
    with Session(history.engine) as db:
        db.get(Conversation, conversation_id).generation_started_at = utcnow() - timedelta(seconds=901)
        db.commit()
        new = start_generation(db, user_id, body, 900)
        result = history.pipe.answer(QUESTION)
        payload = answer_payload(result, history.pipe)
        with pytest.raises(HTTPException) as stale:
            complete_generation(db, old, payload)
        assert stale.value.status_code == 409
        db.rollback()
        complete_generation(db, new, payload)
    messages = history.alice.get(f"/api/chat/conversations/{conversation_id}/messages").json()
    assert len(messages) == 2 and messages[0]["deliveryStatus"] == "completed"


@pytest.mark.skipif(not os.getenv("AUTH_TEST_DATABASE_URL"), reason="PostgreSQL concurrent row-lock check")
def test_parallel_request_is_rejected_but_rename_is_not_blocked_by_model_work(history):
    conversation_id = create(history.alice)
    entered, release = Event(), Event()
    original = history.pipe.answer
    worker = TestClient(app, headers=history.alice.headers)
    worker.cookies.update(history.alice.cookies)

    def blocking_answer(*args, **kwargs):
        entered.set()
        assert release.wait(15)
        return original(*args, **kwargs)

    history.pipe.answer = blocking_answer
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(send, worker, conversation_id)
            try:
                assert entered.wait(10)
                assert send(history.alice, conversation_id).status_code == 409
                assert history.alice.patch(f"/api/chat/conversations/{conversation_id}", json={"title": "While generating"}).status_code == 200
            finally:
                release.set()
            assert pending.result(timeout=15).status_code == 200
    finally:
        release.set()
        worker.close()
