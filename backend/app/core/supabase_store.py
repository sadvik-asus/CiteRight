"""
supabase_store.py
Postgres + pgvector backed vector store, using Supabase as the host.
Implements the same interface as InMemoryVectorStore (add / search) so
document_manager.py and everything downstream (main.py) doesn't need to
know or care which backend is active.

Connection string comes from SUPABASE_DB_URL (see .env.example). If that
env var isn't set, document_manager falls back to InMemoryVectorStore —
this module is only imported/used when persistence is actually configured.
"""

from __future__ import annotations

import os

import psycopg2
from pgvector.psycopg2 import register_vector

from app.core.chunking import Chunk
from app.core.embeddings import embed_texts, embed_query
from app.core.vector_store import SearchResult

_connection = None


def _get_connection():
    """Lazy singleton connection, reused across requests in this process."""
    global _connection
    if _connection is None or _connection.closed:
        db_url = os.environ.get("SUPABASE_DB_URL")
        if not db_url:
            raise RuntimeError("SUPABASE_DB_URL not set — cannot use SupabaseVectorStore.")
        _connection = psycopg2.connect(db_url)
        _connection.autocommit = True
        register_vector(_connection)
    return _connection


class SupabaseVectorStore:
    """
    One instance per document. Mirrors InMemoryVectorStore's interface:
    add(chunks) and search(query, top_k) -> list[SearchResult].
    """

    def __init__(self, document_id: str):
        self.document_id = document_id

    def init_document(self, filename: str) -> None:
        """Insert the parent `documents` row. Call once before add()."""
        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "insert into documents (id, filename, num_chunks) values (%s, %s, %s)",
                (self.document_id, filename, 0),
            )

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = embed_texts([c.text for c in chunks])
        conn = _get_connection()
        with conn.cursor() as cur:
            for chunk, vec in zip(chunks, vectors):
                cur.execute(
                    """
                    insert into chunks (id, document_id, chunk_index, page, source, text, embedding)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (chunk.id, self.document_id, chunk.chunk_index, chunk.page, chunk.source, chunk.text, vec),
                )
            cur.execute(
                "update documents set num_chunks = %s where id = %s",
                (len(chunks), self.document_id),
            )

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        query_vec = embed_query(query)
        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "select id, chunk_index, page, source, text, similarity "
                "from match_chunks(%s, %s, %s)",
                (query_vec, self.document_id, top_k),
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            chunk_id, chunk_index, page, source, text, similarity = row
            chunk = Chunk(
                id=str(chunk_id),
                text=text,
                source=source,
                page=page,
                chunk_index=chunk_index,
            )
            results.append(SearchResult(chunk=chunk, score=float(similarity)))
        return results

    def __len__(self) -> int:
        conn = _get_connection()
        with conn.cursor() as cur:
            cur.execute("select count(*) from chunks where document_id = %s", (self.document_id,))
            (count,) = cur.fetchone()
        return count
