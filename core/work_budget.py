"""Per-call deadlines and stage measurements, without changing RAG algorithms."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

deadline = ContextVar("rag_deadline", default=None)
measurements = ContextVar("rag_measurements", default=None)


def remaining_seconds(default: float) -> float:
    end = deadline.get()
    remaining = default if end is None else min(default, end - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("RAG processing deadline exceeded")
    return remaining


@contextmanager
def stage(name: str):
    started = time.monotonic()
    try:
        remaining_seconds(float("inf"))
        yield
        remaining_seconds(float("inf"))
    finally:
        timings = measurements.get()
        if timings is not None:
            timings[name] = (time.monotonic() - started) * 1000
