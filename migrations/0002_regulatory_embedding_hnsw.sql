-- HNSW accelerates cosine-distance candidate retrieval for normalized embeddings.
ALTER TABLE regulatory_chunks
    ALTER COLUMN embedding TYPE VECTOR(384)
    USING embedding::VECTOR(384);

CREATE INDEX IF NOT EXISTS regulatory_chunks_embedding_hnsw_idx
    ON regulatory_chunks USING HNSW (embedding vector_cosine_ops);