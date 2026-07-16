"""
generation.py
Takes a user query + retrieved chunks, builds a citation-aware prompt,
calls an LLM, and parses the response into (claim, cited_chunk) pairs
ready for the verification layer.

Production backend: Groq API (Llama 3.3 70B), OpenAI-compatible chat
completions endpoint, free tier, fast inference.

Dev fallback: a deterministic "mock LLM" that does extractive
stitching of the retrieved chunks with citation markers. Used when
GROQ_API_KEY is unset or the API is unreachable (e.g. restricted
sandbox network) — lets us test the full prompt -> parse -> verify
pipeline shape without a live API call. Same function signature either
way, so the FastAPI layer above never needs to know which backend ran.

Citation format: the LLM is instructed to tag every sentence with the
retrieved chunk it drew from, using [n] markers that map 1:1 to the
order chunks were given in the prompt, e.g.:
  "RAG reduces hallucination by grounding outputs in real documents. [2]"
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

from app.core.chunking import Chunk
from app.core.vector_store import SearchResult

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


@dataclass
class GeneratedClaim:
    text: str
    cited_chunk: Chunk | None  # None if the LLM cited nothing / an invalid index


@dataclass
class GenerationResult:
    raw_text: str
    claims: list[GeneratedClaim]
    backend_used: str  # "groq" or "mock"


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """You are a careful technical writer. You will be given a set of numbered \
source excerpts and a request. Write a response that is grounded ONLY in the \
provided excerpts — do not use outside knowledge.

Rules:
1. Every sentence that states a fact must end with a citation marker like [1], [2] \
referring to the excerpt number it came from.
2. If you cannot support a claim with the excerpts, do not make that claim.
3. Do not invent citation numbers that don't exist.
4. Write in clear, well-structured prose appropriate for: {mode_description}

{mode_extra_instructions}
"""


def build_prompt(query: str, results: list[SearchResult], mode_description: str, mode_extra_instructions: str = "") -> tuple[str, str]:
    """Returns (system_prompt, user_prompt)."""
    excerpt_lines = []
    for i, r in enumerate(results, start=1):
        page_info = f" (page {r.chunk.page})" if r.chunk.page else ""
        excerpt_lines.append(f"[{i}] (source: {r.chunk.source}{page_info})\n{r.chunk.text}")

    excerpts_block = "\n\n".join(excerpt_lines)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        mode_description=mode_description,
        mode_extra_instructions=mode_extra_instructions,
    )
    user_prompt = f"SOURCE EXCERPTS:\n\n{excerpts_block}\n\nREQUEST:\n{query}"
    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# LLM backends
# ---------------------------------------------------------------------------

def _call_groq(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    resp = httpx.post(
        GROQ_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_mock(results: list[SearchResult]) -> str:
    """
    Deterministic extractive fallback: stitches the first sentence of each
    retrieved chunk together with the correct [n] citation, so the rest of
    the pipeline (parsing, verification) can be tested end-to-end offline.
    This is NOT meant to represent generation quality — just pipeline shape.
    """
    lines = []
    for i, r in enumerate(results, start=1):
        first_sentence = re.split(r"(?<=[.!?])\s", r.chunk.text.strip())[0]
        if not first_sentence.endswith((".", "!", "?")):
            first_sentence += "."
        lines.append(f"{first_sentence} [{i}]")
    return " ".join(lines)


def _generate_raw(query: str, results: list[SearchResult], mode_description: str, mode_extra_instructions: str) -> tuple[str, str]:
    """Returns (raw_text, backend_used)."""
    system_prompt, user_prompt = build_prompt(query, results, mode_description, mode_extra_instructions)
    try:
        text = _call_groq(system_prompt, user_prompt)
        return text, "groq"
    except Exception as e:
        print(f"[generation] Groq call failed ({e}) — using mock fallback for local dev.")
        return _call_mock(results), "mock"


# ---------------------------------------------------------------------------
# Parsing generated text into (claim, cited_chunk) pairs
# ---------------------------------------------------------------------------

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


def parse_claims(raw_text: str, results: list[SearchResult]) -> list[GeneratedClaim]:
    """
    Splits generated text into claims using citation markers [n] as the
    anchor — since the prompt requires every factual sentence to end
    with one, this is more robust than guessing sentence boundaries with
    a capital-letter heuristic (which breaks on abbreviations, lowercase
    continuations, etc). Any trailing text with no citation marker at all
    becomes a final uncited claim.
    """
    index_to_chunk = {i: r.chunk for i, r in enumerate(results, start=1)}

    claims: list[GeneratedClaim] = []
    pos = 0
    for match in CITATION_PATTERN.finditer(raw_text):
        segment = raw_text[pos:match.start()].strip()
        pos = match.end()
        if not segment:
            continue
        chunk = index_to_chunk.get(int(match.group(1)))
        claims.append(GeneratedClaim(text=segment, cited_chunk=chunk))

    # Any leftover text after the last citation marker (or if there were
    # no markers at all) is an uncited claim — but skip it if it's just
    # trailing punctuation/whitespace (e.g. a lone "." left after the
    # final [n] marker), which isn't a real claim.
    tail = raw_text[pos:].strip()
    if tail and re.search(r"[A-Za-z0-9]", tail):
        claims.append(GeneratedClaim(text=tail, cited_chunk=None))

    return claims


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate(
    query: str,
    results: list[SearchResult],
    mode_description: str = "a clear, informative technical article",
    mode_extra_instructions: str = "",
) -> GenerationResult:
    raw_text, backend = _generate_raw(query, results, mode_description, mode_extra_instructions)
    claims = parse_claims(raw_text, results)
    return GenerationResult(raw_text=raw_text, claims=claims, backend_used=backend)


if __name__ == "__main__":
    from app.core.chunking import process_document
    from app.core.vector_store import InMemoryVectorStore

    chunks = process_document("data/sample_docs/rag_intro.txt", chunk_size=80, overlap=15)
    store = InMemoryVectorStore()
    store.add(chunks)

    query = "Explain what RAG is and why chunk size matters."
    results = store.search(query, top_k=4)

    result = generate(query, results)
    print(f"Backend used: {result.backend_used}\n")
    print("RAW OUTPUT:\n", result.raw_text, "\n")
    print("PARSED CLAIMS:")
    for c in result.claims:
        cited = f"chunk page {c.cited_chunk.page}" if c.cited_chunk else "NO CITATION"
        print(f"  - [{cited}] {c.text}")
