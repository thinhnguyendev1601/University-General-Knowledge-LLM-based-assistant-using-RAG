"""LLM clients behind one interface. Ollama (local) is the prototype default; a Claude client
can be added later with the same generate_json() signature without touching the pipeline."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Callable, Protocol
from core.work_budget import remaining_seconds


class LLMClient(Protocol):
    name: str

    def generate_json(self, system: str, user: str, schema: dict) -> dict: ...


class OllamaClient:
    def __init__(self, model: str = "llama3.2", url: str = "http://localhost:11434", num_ctx: int = 8192,
                 timeout: float = 600):
        self.name = f"ollama:{model}"
        self.model, self.url, self.num_ctx, self.timeout = model, url.rstrip("/"), num_ctx, timeout

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "format": schema,  # Ollama structured outputs: the reply is forced to match this JSON schema
            "stream": False,
            "options": {"temperature": 0, "seed": 0, "num_ctx": self.num_ctx},
        }
        req = urllib.request.Request(f"{self.url}/api/chat", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=remaining_seconds(self.timeout)) as r:
                content = json.loads(r.read())["message"]["content"]
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama not reachable at {self.url} ({e}); is `ollama serve` running and "
                               f"`ollama pull {self.model}` done?") from e
        return json.loads(content)


class FakeLLM:
    """For tests: returns whatever the callback builds from (system, user)."""

    def __init__(self, fn: Callable[[str, str], dict]):
        self.name, self.fn = "fake", fn

    def generate_json(self, system: str, user: str, schema: dict) -> dict:
        return self.fn(system, user)
