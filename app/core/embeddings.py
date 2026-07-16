"""
embeddings.py
Wraps a text-embedding backend for encoding text into vectors.

Production backend: sentence-transformers (all-MiniLM-L6-v2), 384-dim,
free, fast on CPU. This is what runs on Render in deployment.

Dev fallback: TF-IDF (scikit-learn), used automatically when the
sentence-transformers model can't be downloaded (e.g. restricted network
in a sandboxed dev environment). Same function signature either way, so
nothing downstream (vector_store, retrieval, generation) has to change
when we switch backends.

Set EMBEDDING_BACKEND=tfidf explicitly to force the fallback; otherwise
this module auto-detects by trying to load the real model first.
"""

from __future__ import annotations

import os

import numpy as np

_MODEL_NAME = "all-MiniLM-L6-v2"
_backend = os.environ.get("EMBEDDING_BACKEND")  # "sentence-transformers" | "tfidf" | None (auto)

_model = None             # sentence-transformers model, if loaded
_tfidf_vectorizer = None  # sklearn TfidfVectorizer, if using fallback


def _try_load_sentence_transformer():
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _get_backend() -> str:
    """Resolve which backend to use, caching the decision in _backend."""
    global _backend
    if _backend is not None:
        return _backend
    try:
        _try_load_sentence_transformer()
        _backend = "sentence-transformers"
    except Exception:
        _backend = "tfidf"
        print(
            "[embeddings] Could not reach sentence-transformers/HF Hub — "
            "falling back to TF-IDF for local dev. Production deployment "
            "will use sentence-transformers (see EMBEDDING_BACKEND env var)."
        )
    return _backend


def get_model():
    """Lazy-load the embedding model (singleton so we don't reload per call)."""
    return _try_load_sentence_transformer()


def _embed_tfidf(texts: list[str]) -> np.ndarray:
    """
    TF-IDF fallback for local dev/testing only (no persistent vocabulary
    across calls — not meant for production). Vectors are L2-normalized
    so dot product == cosine similarity.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    global _tfidf_vectorizer
    if _tfidf_vectorizer is None:
        _tfidf_vectorizer = TfidfVectorizer(max_features=4096)
        _tfidf_vectorizer.fit(texts)

    vecs = _tfidf_vectorizer.transform(texts).toarray().astype(np.float32)
    vecs = normalize(vecs)
    return vecs


def reset_tfidf_vocab():
    """Call before indexing a new document/corpus in tfidf dev mode."""
    global _tfidf_vectorizer
    _tfidf_vectorizer = None


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts. Returns L2-normalized vectors."""
    backend = _get_backend()
    if backend == "tfidf":
        return _embed_tfidf(texts)

    model = get_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string. NOTE: in tfidf dev mode, call
    embed_texts() on the full corpus first so the vectorizer vocabulary
    is fit before embedding a query against it."""
    backend = _get_backend()
    if backend == "tfidf":
        global _tfidf_vectorizer
        if _tfidf_vectorizer is None:
            raise RuntimeError(
                "TF-IDF vectorizer not fit yet — embed corpus texts before a query."
            )
        from sklearn.preprocessing import normalize
        vec = _tfidf_vectorizer.transform([text]).toarray().astype(np.float32)
        return normalize(vec)[0]
    return embed_texts([text])[0]


if __name__ == "__main__":
    vecs = embed_texts(["Retrieval-augmented generation grounds LLM outputs in real documents."])
    print("Embedding shape:", vecs.shape)
    print("Backend:", _get_backend())
