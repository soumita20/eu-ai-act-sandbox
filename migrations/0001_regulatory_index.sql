CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS regulatory_index_versions (
    index_version TEXT PRIMARY KEY,
    schema_version TEXT NOT NULL,
    manifest JSONB NOT NULL,
    publication_status TEXT NOT NULL CHECK (publication_status IN ('BUILDING', 'PUBLISHED')),
    published_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS regulatory_chunks (
    index_version TEXT NOT NULL REFERENCES regulatory_index_versions(index_version),
    chunk_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    document_version_id TEXT NOT NULL,
    article_reference TEXT NULL,
    content TEXT NOT NULL,
    text_hash CHAR(64) NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    parent_reference TEXT NULL,
    source_authority TEXT NOT NULL,
    language TEXT NOT NULL,
    effective_from DATE NULL,
    effective_to DATE NULL,
    source_coordinates JSONB NOT NULL,
    embedding_model_id TEXT NOT NULL,
    embedding_model_revision TEXT NOT NULL,
    embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions > 0),
    preprocessing_version TEXT NOT NULL,
    embedding_library_version TEXT NOT NULL,
    execution_device TEXT NOT NULL,
    embedding VECTOR NOT NULL,
    PRIMARY KEY (index_version, chunk_id),
    CHECK (vector_dims(embedding) = embedding_dimensions),
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from)
);

CREATE INDEX IF NOT EXISTS regulatory_chunks_version_source_idx
    ON regulatory_chunks (index_version, source_id, document_version_id, chunk_index);

CREATE INDEX IF NOT EXISTS regulatory_chunks_content_fts_gin_idx
    ON regulatory_chunks USING GIN (to_tsvector('simple', content));
