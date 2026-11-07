"""Corpus loading + dense retrieval (bge-m3, in-memory, cached to disk).

In-memory numpy stands in for pgvector during the prototype (CLAUDE.md §3 allows a throwaway
index behind the same interface). Only role=indexed documents are ever loaded (A2).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

import numpy as np

from core.schemas import Chunk, DocumentMeta, ScoredChunk
from eval.testset import load_manifest
from rag.chunker import chunk_file


def load_indexed_chunks(processed_dir: str, manifest: str) -> tuple[list[Chunk], dict[str, DocumentMeta]]:
    meta = load_manifest(Path(manifest))
    chunks: list[Chunk] = []
    for doc_id, m in sorted(meta.items()):
        if m.role != "indexed":
            continue
        p = Path(processed_dir) / f"{doc_id}.txt"
        if not p.exists():
            raise SystemExit(f"{doc_id} is indexed in the manifest but {p} is missing (run scripts/extract_text.py)")
        chunks += chunk_file(p, m.lang if m.lang != "mixed" else "en", m.doc_version)
    return chunks, meta


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> np.ndarray: ...  # (n, dim), L2-normalised


class BgeM3Embedder:
    def __init__(self, model: str = "BAAI/bge-m3", max_seq_length: int = 1024, batch_size: int = 8):
        from sentence_transformers import SentenceTransformer  # heavy import, only when used

        self.name = model
        self.model = SentenceTransformer(model, device="cpu")
        self.model.max_seq_length = max_seq_length
        self.batch_size = batch_size

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                            show_progress_bar=len(texts) > 50), dtype=np.float32)


class DenseIndex:
    """Cosine similarity over chunk.embedding_text() (section path + text)."""

    def __init__(self, chunks: list[Chunk], embedder: Embedder, cache_dir: str | None = "data/index"):
        self.chunks, self.embedder = chunks, embedder
        texts = [c.embedding_text() for c in chunks]
        # cache key = model + every text that gets embedded -> any chunker/corpus change re-embeds
        key = hashlib.sha256("\x00".join([embedder.name, *texts]).encode("utf-8")).hexdigest()[:16]
        path = Path(cache_dir) / f"{embedder.name.replace('/', '_')}-{key}.npy" if cache_dir else None
        if path and path.exists():
            self.vecs = np.load(path)
        else:
            self.vecs = embedder.encode(texts)
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                np.save(path, self.vecs)

    def search(self, query: str, k: int = 10, doc_ids: set[str] | None = None) -> list[ScoredChunk]:
        """doc_ids = metadata filter (e.g. one institution's documents); None = whole index."""
        q = self.embedder.encode([query])[0]
        sims = self.vecs @ q
        if doc_ids is not None:
            sims = np.where([c.doc_id in doc_ids for c in self.chunks], sims, -np.inf)
        top = [i for i in np.argsort(-sims)[:k] if np.isfinite(sims[i])]
        return [ScoredChunk(chunk=self.chunks[i], score=round(float(sims[i]), 4), rank=r, source="dense")
                for r, i in enumerate(top, 1)]
