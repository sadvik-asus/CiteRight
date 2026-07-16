"""
vector_store.py
A simple in-memory vector store for local development/testing.
Same interface (add / search) will be mirrored by a Supabase pgvector
implementation in production — swapping backends won't touch the
retrieval or generation logic above this layer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.chunking import Chunk
from app.core.embeddings import embed_texts, embed_query


@dataclass
class SearchResult:
    chunk: Chunk
    score: float  # cosine similarity, higher = more relevant


class InMemoryVectorStore:
    def __init__(self):
        self._chunks: list[Chunk] = []
        self._vectors: np.ndarray | None = None

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = embed_texts([c.text for c in chunks])
        if self._vectors is None:
            self._vectors = vectors
        else:
            self._vectors = np.vstack([self._vectors, vectors])
        self._chunks.extend(chunks)

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        if self._vectors is None or len(self._chunks) == 0:
            return []
        q_vec = embed_query(query)
        # vectors are normalized, so dot product = cosine similarity
        scores = self._vectors @ q_vec
        top_idx = np.argsort(-scores)[:top_k]
        return [SearchResult(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx]

    def __len__(self) -> int:
        return len(self._chunks)


if __name__ == "__main__":
    from app.core.chunking import process_document
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vector_store.py <path_to_document>")
        sys.exit(1)

    store = InMemoryVectorStore()
    chunks = process_document(sys.argv[1])
    store.add(chunks)
    print(f"Indexed {len(store)} chunks.")

    query = "What is retrieval-augmented generation?"
    results = store.search(query, top_k=3)
    for r in results:
        print(f"\n[score={r.score:.3f}] page {r.chunk.page}")
        print(r.chunk.text[:200], "...")
