"""Bounded queue, timeout containment and recovery, using events rather than a live model."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
import time
import uuid

import pytest

from api.app import app
from api.rag_admission import RagAdmission, RagBusy, RagTimedOut, get_admission
from api.settings import Settings, get_settings
from core.work_budget import deadline, remaining_seconds, stage
from tests.test_auth import account
from tests.test_conversations import history, create, send


@pytest.fixture
def lane():
    admission = RagAdmission()
    yield admission
    admission.close()


def run(lane, call, **options):
    return lane.run(call, max_waiting=options.get("max_waiting", 1),
                    queue_timeout=options.get("queue_timeout", .2),
                    processing_timeout=options.get("processing_timeout", 2), timings=options.get("timings", {}))


def test_queue_full_and_expired_waiter_never_runs(lane):
    entered, release = Event(), Event()
    calls = []

    def hold():
        entered.set()
        release.wait(3)

    try:
        with ThreadPoolExecutor(2) as pool:
            first = pool.submit(run, lane, hold)
            assert entered.wait(1)
            second = pool.submit(run, lane, lambda: calls.append("must not run"), queue_timeout=.1)
            with lane.condition:
                assert lane.condition.wait_for(lambda: len(lane.queue) == 1, 1)
            with pytest.raises(RagBusy):
                run(lane, lambda: calls.append("overflow"))
            with pytest.raises(RagBusy):
                second.result(1)
            release.set()
            first.result(1)
        assert not calls
        assert run(lane, lambda: "recovered") == "recovered"
    finally:
        release.set()


def test_timed_out_work_retains_capacity_until_it_really_finishes(lane):
    entered, release = Event(), Event()

    def hold():
        entered.set()
        release.wait(3)
        return "late result"

    try:
        with pytest.raises(RagTimedOut):
            run(lane, hold, processing_timeout=.03, max_waiting=0)
        assert entered.is_set() and lane.running
        with pytest.raises(RagBusy):
            run(lane, lambda: "cannot overlap", max_waiting=0)
        release.set()
        with lane.condition:
            assert lane.condition.wait_for(lambda: not lane.running, 1)
        assert run(lane, lambda: "new result") == "new result"
    finally:
        release.set()


def test_metrics_and_deadline_are_per_task_and_errors_recover(lane):
    timings = {}

    def measured():
        assert 0 < remaining_seconds(100) <= 2
        with stage("retrievalMs"):
            time.sleep(.001)
        with stage("generationMs"):
            time.sleep(.001)
        return "ok"

    assert run(lane, measured, timings=timings) == "ok"
    assert all(timings[key] >= 0 for key in ("queueMs", "processingMs", "retrievalMs", "generationMs"))
    assert deadline.get() is None
    with pytest.raises(ValueError):
        run(lane, lambda: (_ for _ in ()).throw(ValueError("failed")))
    assert run(lane, lambda: "recovered") == "recovered"


def test_timeout_api_keeps_question_retries_once_and_discards_late_result(history, lane):
    client = history.alice
    conversation = create(client)
    request_id = str(uuid.uuid4())
    original = history.pipe.answer
    release = Event()
    app.dependency_overrides[get_admission] = lambda: lane
    settings = replace(Settings(rag_enabled=False), chat_max_waiting=0,
                       chat_queue_timeout_seconds=.1, chat_processing_timeout_seconds=.04)
    app.dependency_overrides[get_settings] = lambda: settings

    def blocked(*args, **kwargs):
        release.wait(3)
        return original(*args, **kwargs)

    history.pipe.answer = blocked
    try:
        response = send(client, conversation, requestId=request_id)
        assert response.status_code == 504 and response.headers["Retry-After"] == "5"
        saved = client.get(f"/api/chat/conversations/{conversation}/messages").json()
        assert len(saved) == 1 and saved[0]["errorCode"] == "rag_timeout"
        assert send(client, conversation, requestId=request_id).status_code == 503
        release.set()
        with lane.condition:
            assert lane.condition.wait_for(lambda: not lane.running, 2)
        # The completed old model call has no callback that can write a late answer.
        assert len(client.get(f"/api/chat/conversations/{conversation}/messages").json()) == 1
        history.pipe.answer = original
        app.dependency_overrides[get_settings] = lambda: replace(settings, chat_processing_timeout_seconds=2)
        response = send(client, conversation, requestId=request_id)
        assert response.status_code == 200 and "retrieval;dur=" in response.headers["Server-Timing"]
        messages = client.get(f"/api/chat/conversations/{conversation}/messages").json()
        assert len(messages) == 2 and messages[0]["id"] == saved[0]["id"]
        assert send(client, conversation, requestId=request_id).json()["id"] == response.json()["id"]
    finally:
        release.set()


def test_frontend_timeout_configuration_requires_login(history):
    result = history.alice.get("/api/chat/config")
    assert result.status_code == 200
    assert result.json()["requestTimeoutMs"] == 220000
    assert result.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize("changes", [
    {"chat_max_waiting": -1}, {"chat_max_waiting": 33},
    {"chat_queue_timeout_seconds": 0}, {"chat_processing_timeout_seconds": float("nan")},
    {"chat_processing_timeout_seconds": float("inf")}, {"chat_generation_lease_seconds": 200},
])
def test_invalid_queue_and_lease_settings(changes):
    with pytest.raises(ValueError):
        Settings(**changes)
