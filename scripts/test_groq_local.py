"""
test_groq_local.py
Run this ON YOUR OWN MACHINE (not in a restricted sandbox) to verify your
GROQ_API_KEY works and to see real (non-mock) generation quality.

Setup:
  1. cd citeright
  2. python3 -m venv venv && source venv/bin/activate   (or venv\\Scripts\\activate on Windows)
  3. pip install -r requirements.txt
  4. cp .env.example .env   and paste your real GROQ_API_KEY into .env
  5. python3 test_groq_local.py
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()  # reads .env into environment

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.chunking import process_document
from app.core.vector_store import InMemoryVectorStore
from app.core.generation import generate
from app.core.verification import verify_generated_text


def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    print("Indexing sample document...")
    chunks = process_document("data/sample_docs/rag_intro.txt", chunk_size=80, overlap=15)
    store = InMemoryVectorStore()
    store.add(chunks)
    print(f"Indexed {len(store)} chunks.\n")

    query = "Explain what RAG is and why chunk size matters."
    print(f"QUERY: {query}\n")

    results = store.search(query, top_k=4)
    gen_result = generate(query, results)

    print(f"Backend used: {gen_result.backend_used}")
    if gen_result.backend_used == "mock":
        print("!! Still using mock fallback — check your API key / internet connection.\n")
    else:
        print("Live Groq generation successful.\n")

    print("=" * 70)
    print("RAW GENERATED TEXT:")
    print("=" * 70)
    print(gen_result.raw_text)
    print()

    claim_chunk_pairs = [(c.text, c.cited_chunk) for c in gen_result.claims]
    verifications, trust_score = verify_generated_text(claim_chunk_pairs)

    print("=" * 70)
    print("VERIFICATION BREAKDOWN:")
    print("=" * 70)
    for v in verifications:
        print(f"[{v.support_level.value.upper():12}] score={v.score:.3f}  {v.claim_text[:90]}")

    print(f"\nOVERALL TRUST SCORE: {trust_score:.2f}")


if __name__ == "__main__":
    main()
