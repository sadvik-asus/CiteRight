"""
main.py
FastAPI app exposing CiteRight's pipeline: upload a document, generate
cited content in one of 3 modes, get back the draft plus a per-claim
verification breakdown and overall trust score.

Run locally with:  uvicorn app.main:app --reload
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read GROQ_API_KEY at call time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.document_manager import document_manager
from app.core.generation import generate
from app.core.verification import verify_generated_text
from app.modes.config import MODE_CONFIGS, Mode, get_mode_config

app = FastAPI(
    title="CiteRight API",
    description="RAG-powered content generation with verifiable, per-claim citations.",
    version="0.1.0",
)

# Wide-open CORS for the demo deployment (Vercel frontend calling Render backend).
# Tighten to specific origin(s) once the frontend URL is finalized.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    num_chunks: int


class GenerateRequest(BaseModel):
    document_id: str
    query: str
    mode: Mode = Mode.GENERAL


class ClaimResult(BaseModel):
    text: str
    support_level: str
    score: float
    cited_source: str | None
    cited_page: int | None
    cited_excerpt: str | None


class GenerateResponse(BaseModel):
    raw_text: str
    claims: list[ClaimResult]
    trust_score: float
    backend_used: str
    mode: Mode


class ModeInfo(BaseModel):
    id: str
    label: str
    description: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/modes", response_model=list[ModeInfo])
def list_modes():
    return [
        ModeInfo(id=cfg.id.value, label=cfg.label, description=cfg.description)
        for cfg in MODE_CONFIGS.values()
    ]


@app.post("/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), mode: Mode = Mode.GENERAL):
    """
    Uploads and indexes a document, chunked using the parameters of the
    given mode (different modes prefer different chunk sizes).
    """
    if not file.filename.lower().endswith((".pdf", ".txt", ".md")):
        raise HTTPException(status_code=400, detail="Only .pdf, .txt, .md files are supported.")

    cfg = get_mode_config(mode)
    file_bytes = await file.read()

    try:
        record = document_manager.add_document(
            file_bytes=file_bytes,
            filename=file.filename,
            chunk_size=cfg.chunk_size,
            chunk_overlap=cfg.chunk_overlap,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process document: {e}")

    return UploadResponse(document_id=record.id, filename=record.filename, num_chunks=record.num_chunks)


@app.post("/generate", response_model=GenerateResponse)
def generate_content(req: GenerateRequest):
    record = document_manager.get_document(req.document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found. Upload it first via /documents/upload.")

    cfg = get_mode_config(req.mode)
    results = record.store.search(req.query, top_k=cfg.top_k)
    if not results:
        raise HTTPException(status_code=422, detail="No relevant content found in the document for this query.")

    gen_result = generate(
        query=req.query,
        results=results,
        mode_description=cfg.mode_description,
        mode_extra_instructions=cfg.mode_extra_instructions,
    )

    claim_chunk_pairs = [(c.text, c.cited_chunk) for c in gen_result.claims]
    verifications, trust_score = verify_generated_text(claim_chunk_pairs)

    claims_out = [
        ClaimResult(
            text=v.claim_text,
            support_level=v.support_level.value,
            score=round(v.score, 3),
            cited_source=next((c.cited_chunk.source for c in gen_result.claims if c.text == v.claim_text and c.cited_chunk), None),
            cited_page=next((c.cited_chunk.page for c in gen_result.claims if c.text == v.claim_text and c.cited_chunk), None),
            cited_excerpt=next((c.cited_chunk.text for c in gen_result.claims if c.text == v.claim_text and c.cited_chunk), None),
        )
        for v in verifications
    ]

    return GenerateResponse(
        raw_text=gen_result.raw_text,
        claims=claims_out,
        trust_score=round(trust_score, 3),
        backend_used=gen_result.backend_used,
        mode=req.mode,
    )
