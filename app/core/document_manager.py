"""
document_manager.py
Manages the lifecycle of uploaded documents: saving, chunking, indexing,
and keeping them retrievable by a document_id for later /generate calls.

Backend selection: if SUPABASE_DB_URL is set, documents are persisted in
Supabase (Postgres + pgvector) and survive server restarts. Otherwise,
falls back to an in-memory store (fine for local dev, but documents are
lost whenever the process restarts). Same pattern used elsewhere in this
project (embeddings, generation) — graceful degradation with a clear
console message about which backend is active.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.chunking import process_document
from app.core.vector_store import InMemoryVectorStore

UPLOAD_DIR = Path("/tmp/citeright_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_USE_SUPABASE = bool(os.environ.get("SUPABASE_DB_URL"))
if _USE_SUPABASE:
    from app.core.supabase_store import SupabaseVectorStore, _get_connection
    print("[document_manager] SUPABASE_DB_URL set — using persistent Supabase pgvector store.")
else:
    print("[document_manager] SUPABASE_DB_URL not set — using in-memory store (documents won't survive a restart).")


@dataclass
class DocumentRecord:
    id: str
    filename: str
    num_chunks: int
    store: object = field(repr=False)  # InMemoryVectorStore or SupabaseVectorStore


class DocumentManager:
    def __init__(self):
        self._documents: dict[str, DocumentRecord] = {}

    def add_document(self, file_bytes: bytes, filename: str, chunk_size: int, chunk_overlap: int) -> DocumentRecord:
        doc_id = str(uuid.uuid4())
        save_path = UPLOAD_DIR / f"{doc_id}_{filename}"
        save_path.write_bytes(file_bytes)

        chunks = process_document(save_path, chunk_size=chunk_size, overlap=chunk_overlap)
        for c in chunks:
            c.source = filename  # cite the original filename, not the UUID-prefixed save path

        if _USE_SUPABASE:
            store = SupabaseVectorStore(doc_id)
            store.init_document(filename)
            store.add(chunks)
        else:
            store = InMemoryVectorStore()
            store.add(chunks)

        record = DocumentRecord(id=doc_id, filename=filename, num_chunks=len(chunks), store=store)
        self._documents[doc_id] = record
        return record

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        if doc_id in self._documents:
            return self._documents[doc_id]

        # Not in this process's memory — if Supabase is configured, the
        # document may still exist from before a restart. Check there.
        if _USE_SUPABASE:
            conn = _get_connection()
            with conn.cursor() as cur:
                cur.execute("select filename, num_chunks from documents where id = %s", (doc_id,))
                row = cur.fetchone()
            if row is None:
                return None
            filename, num_chunks = row
            store = SupabaseVectorStore(doc_id)
            record = DocumentRecord(id=doc_id, filename=filename, num_chunks=num_chunks, store=store)
            self._documents[doc_id] = record  # cache for this process going forward
            return record

        return None

    def list_documents(self) -> list[DocumentRecord]:
        return list(self._documents.values())


# Module-level singleton. With Supabase configured, the underlying data is
# shared/persistent across processes; this dict is just a per-process cache
# on top of it (see get_document's DB fallback above).
document_manager = DocumentManager()
