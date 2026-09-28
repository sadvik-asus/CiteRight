"""
chunking.py
Handles document ingestion (PDF/txt) and splits text into overlapping,
citation-friendly chunks. Each chunk keeps metadata (source file, page
number, chunk index) so later generation steps can cite it precisely.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader


@dataclass
class Chunk:
    id: str
    text: str
    source: str          # filename
    page: int | None      # page number if known (1-indexed), else None
    chunk_index: int      # order within the document
    metadata: dict = field(default_factory=dict)


def _clean_text(text: str) -> str:
    """Normalize whitespace, strip weird PDF artifacts."""
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def load_pdf(path: str | Path) -> list[tuple[int, str]]:
    """Returns list of (page_number, page_text) tuples, 1-indexed pages."""
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        cleaned = _clean_text(raw)
        if cleaned:
            pages.append((i, cleaned))
    return pages


def load_txt(path: str | Path) -> list[tuple[int, str]]:
    """Plain text files have no real pages — treat whole file as page 1."""
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return [(1, _clean_text(text))]


def load_document(path: str | Path) -> list[tuple[int, str]]:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    elif suffix in (".txt", ".md"):
        return load_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def chunk_text(
    text: str,
    chunk_size: int = 220,
    overlap: int = 40,
) -> list[str]:
    """
    Splits text into overlapping chunks by word count.
    chunk_size / overlap are in words, not tokens — good enough approximation
    for MiniLM's 256-token context window.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == len(words):
            break
        start = end - overlap  # step forward with overlap
    return chunks


def process_document(path: str | Path, chunk_size: int = 220, overlap: int = 40) -> list[Chunk]:
    """
    Full pipeline: load a document, split each page into chunks,
    and return a flat list of Chunk objects ready for embedding.
    """
    path = Path(path)
    pages = load_document(path)

    chunks: list[Chunk] = []
    idx = 0
    for page_num, page_text in pages:
        for piece in chunk_text(page_text, chunk_size, overlap):
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    text=piece,
                    source=path.name,
                    page=page_num,
                    chunk_index=idx,
                )
            )
            idx += 1
    return chunks


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python chunking.py <path_to_document>")
        sys.exit(1)

    result = process_document(sys.argv[1])
    print(f"Produced {len(result)} chunks from {sys.argv[1]}")
    for c in result[:3]:
        print(f"\n--- Chunk {c.chunk_index} (page {c.page}) ---")
        print(c.text[:200], "...")
