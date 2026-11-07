"""One bounded RAG lane per API process. Timed-out work keeps its lane until done."""
from collections import deque
from dataclasses import dataclass, field
import threading
import time
from typing import Callable

from core.work_budget import deadline, measurements


class RagBusy(Exception):
    pass


class RagTimedOut(Exception):
    pass


@dataclass
class Task:
    call: Callable
    timeout: float
    timings: dict
    submitted: float = field(default_factory=time.monotonic)
    started: threading.Event = field(default_factory=threading.Event)
    done: threading.Event = field(default_factory=threading.Event)
    started_at: float | None = None
    result: object = None
    error: Exception | None = None


class RagAdmission:
    def __init__(self):
        self.condition = threading.Condition()
        self.queue = deque()
        self.running = False
        self.closed = False
        self.thread = threading.Thread(target=self._work, name="rag-lane", daemon=True)
        self.thread.start()

    def run(self, call, *, max_waiting, queue_timeout, processing_timeout, timings):
        task = Task(call=call, timeout=processing_timeout, timings=timings)
        with self.condition:
            if self.closed or len(self.queue) + int(self.running) >= 1 + max_waiting:
                raise RagBusy()
            self.queue.append(task)
            self.condition.notify()
        if not task.started.wait(queue_timeout):
            with self.condition:
                if task.started_at is None:
                    self.queue.remove(task)
                    timings["queueMs"] = (time.monotonic() - task.submitted) * 1000
                    raise RagBusy()
        remaining = task.started_at + processing_timeout - time.monotonic()
        if not task.done.wait(max(0, remaining)) or time.monotonic() > task.started_at + processing_timeout:
            raise RagTimedOut()
        if isinstance(task.error, TimeoutError):
            raise RagTimedOut() from task.error
        if task.error is not None:
            raise task.error
        return task.result

    def _work(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.queue or self.closed)
                if self.closed:
                    return
                task = self.queue.popleft()
                self.running = True
                task.started_at = time.monotonic()
                task.timings["queueMs"] = (task.started_at - task.submitted) * 1000
                task.started.set()
            deadline_token = deadline.set(task.started_at + task.timeout)
            timings_token = measurements.set(task.timings)
            try:
                task.result = task.call()
            except Exception as error:
                task.error = error
            finally:
                task.timings["processingMs"] = (time.monotonic() - task.started_at) * 1000
                measurements.reset(timings_token)
                deadline.reset(deadline_token)
                with self.condition:
                    self.running = False
                    task.done.set()
                    self.condition.notify_all()

    def close(self):
        with self.condition:
            self.closed = True
            # Wake queued callers. An active call never writes database state itself.
            while self.queue:
                task = self.queue.popleft()
                task.error = RagBusy()
                task.started_at = time.monotonic()
                task.started.set()
                task.done.set()
            self.condition.notify_all()


_instance = None
_lock = threading.Lock()


def get_admission() -> RagAdmission:
    global _instance
    with _lock:
        if _instance is None:
            _instance = RagAdmission()
        return _instance


def shutdown_admission():
    global _instance
    with _lock:
        if _instance is not None:
            _instance.close()
            _instance = None
