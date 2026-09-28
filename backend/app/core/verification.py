"""
verification.py
The "hallucination firewall" core: given a generated claim (a sentence)
and the source chunk it was supposedly grounded in, score how well the
claim is actually supported by that source.

Method: semantic similarity between claim and cited chunk, using the
same embedding backend as retrieval. This is a lightweight proxy for
"entailment" — not as rigorous as a trained NLI model, but free, fast,
and good enough to catch clear hallucinations (claims that drift far
from their cited source).

Design note: this is intentionally pluggable. verify_claim() is the
single seam — swapping in a proper NLI model (e.g. a cross-encoder
fine-tuned for entailment) later only requires changing this function,
nothing upstream or downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import numpy as np

from app.core.chunking import Chunk
from app.core.embeddings import embed_texts


class SupportLevel(str, Enum):
    SUPPORTED = "supported"      # score >= high threshold
    WEAK = "weak"                # score between low and high threshold
    UNSUPPORTED = "unsupported"  # score < low threshold


# Thresholds are conservative starting points — tune later against a
# small labeled eval set (Phase-2b: build ~20 hand-labeled examples).
HIGH_THRESHOLD = 0.55
LOW_THRESHOLD = 0.30


@dataclass
class ClaimVerification:
    claim_text: str
    cited_chunk_id: str | None
    score: float
    support_level: SupportLevel


def split_into_claims(text: str) -> list[str]:
    """
    Naive sentence splitter. Good enough for claim-level granularity;
    swap for a proper sentence tokenizer (e.g. nltk/spacy) if generated
    text gets more complex (abbreviations, decimals, etc).
    """
    # Split on '.', '!', '?' followed by whitespace + capital letter,
    # but keep it simple — good enough for LLM-generated prose.
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z(\[])", text.strip())
    return [s.strip() for s in raw if s.strip()]


def verify_claim(claim_text: str, cited_chunk: Chunk | None) -> ClaimVerification:
    """
    Score a single claim against its cited source chunk.
    If no chunk was cited, it's automatically unsupported.
    """
    if cited_chunk is None:
        return ClaimVerification(
            claim_text=claim_text,
            cited_chunk_id=None,
            score=0.0,
            support_level=SupportLevel.UNSUPPORTED,
        )

    vecs = embed_texts([claim_text, cited_chunk.text])
    claim_vec, source_vec = vecs[0], vecs[1]
    score = float(np.dot(claim_vec, source_vec))

    if score >= HIGH_THRESHOLD:
        level = SupportLevel.SUPPORTED
    elif score >= LOW_THRESHOLD:
        level = SupportLevel.WEAK
    else:
        level = SupportLevel.UNSUPPORTED

    return ClaimVerification(
        claim_text=claim_text,
        cited_chunk_id=cited_chunk.id,
        score=score,
        support_level=level,
    )


def verify_generated_text(
    claims_with_citations: list[tuple[str, Chunk | None]],
) -> tuple[list[ClaimVerification], float]:
    """
    Verify a full generated response: list of (claim_text, cited_chunk) pairs.
    Returns (per-claim verifications, overall trust_score 0-1).

    trust_score = fraction of claims that are SUPPORTED, with WEAK claims
    counted as half-credit. This is a simple, explainable metric —
    good for a portfolio demo where you want to show the number and
    explain exactly how it's computed.
    """
    results = [verify_claim(text, chunk) for text, chunk in claims_with_citations]

    if not results:
        return results, 0.0

    credit = 0.0
    for r in results:
        if r.support_level == SupportLevel.SUPPORTED:
            credit += 1.0
        elif r.support_level == SupportLevel.WEAK:
            credit += 0.5
        # UNSUPPORTED contributes 0

    trust_score = credit / len(results)
    return results, trust_score


if __name__ == "__main__":
    from app.core.chunking import process_document

    chunks = process_document("data/sample_docs/rag_intro.txt", chunk_size=80, overlap=15)

    # Simulate: one claim well-supported by chunk[0], one hallucinated
    good_claim = "RAG combines information retrieval with text generation to reduce hallucination."
    bad_claim = "RAG was invented by IBM in 2015 specifically for chatbots."

    test_pairs = [
        (good_claim, chunks[0]),
        (bad_claim, chunks[0]),
    ]

    results, trust = verify_generated_text(test_pairs)
    for r in results:
        print(f"[{r.support_level.value.upper()}] score={r.score:.3f}")
        print(f"  claim: {r.claim_text}\n")

    print(f"Overall trust score: {trust:.2f}")
