-- CiteRight database schema
-- Run this in Supabase SQL Editor (Dashboard -> SQL Editor -> New query)

-- Enable pgvector (should already be on if you enabled it via Database -> Extensions,
-- but this is safe to run again either way)
create extension if not exists vector;

-- One row per uploaded document
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    filename text not null,
    num_chunks integer not null default 0,
    created_at timestamptz not null default now()
);

-- One row per chunk, with its embedding
create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index integer not null,
    page integer,
    source text not null,
    text text not null,
    embedding vector(384),  -- 384 = all-MiniLM-L6-v2 output dimension
    created_at timestamptz not null default now()
);

-- Index for fast similarity search (IVFFlat, cosine distance)
-- Note: IVFFlat indexes need existing data to build well; with small demo-scale
-- data this still works fine, just less optimized than at large scale.
create index if not exists chunks_embedding_idx
    on chunks using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

-- Speed up "get all chunks for a document" lookups
create index if not exists chunks_document_id_idx
    on chunks (document_id);

-- Similarity search function: given a query embedding and a document_id,
-- return the top-k most similar chunks (cosine similarity, higher = closer).
create or replace function match_chunks (
    query_embedding vector(384),
    match_document_id uuid,
    match_count int default 6
)
returns table (
    id uuid,
    chunk_index integer,
    page integer,
    source text,
    text text,
    similarity float
)
language sql stable
as $$
    select
        chunks.id,
        chunks.chunk_index,
        chunks.page,
        chunks.source,
        chunks.text,
        1 - (chunks.embedding <=> query_embedding) as similarity
    from chunks
    where chunks.document_id = match_document_id
    order by chunks.embedding <=> query_embedding
    limit match_count;
$$;
