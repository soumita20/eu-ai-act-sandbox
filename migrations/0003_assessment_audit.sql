CREATE TABLE IF NOT EXISTS assessment_runs (
    assessment_id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    assessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    as_of_date DATE NOT NULL,
    assessment_mode TEXT NOT NULL,
    legal_basis_version TEXT NOT NULL,
    control_catalog_version TEXT NOT NULL,
    assessment_status TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    result_json JSONB NOT NULL,
    result_sha256 CHAR(64) NOT NULL
);

CREATE INDEX IF NOT EXISTS assessment_runs_recent_idx
    ON assessment_runs (assessed_at DESC, assessment_id DESC);

CREATE TABLE IF NOT EXISTS assessment_control_results (
    assessment_id TEXT NOT NULL REFERENCES assessment_runs(assessment_id) ON DELETE CASCADE,
    control_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    PRIMARY KEY (assessment_id, control_id)
);

CREATE TABLE IF NOT EXISTS assessment_regulatory_evidence (
    assessment_id TEXT NOT NULL REFERENCES assessment_runs(assessment_id) ON DELETE CASCADE,
    control_id TEXT NOT NULL,
    evidence_position INTEGER NOT NULL CHECK (evidence_position >= 0),
    query_text TEXT NOT NULL,
    chunk_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    document_version_id TEXT NOT NULL,
    article_reference TEXT NULL,
    source_coordinates JSONB NOT NULL,
    text_hash CHAR(64) NOT NULL,
    index_version TEXT NOT NULL,
    embedding_model_id TEXT NOT NULL,
    embedding_model_revision TEXT NOT NULL,
    source_authority TEXT NOT NULL,
    language TEXT NOT NULL,
    effective_from DATE NULL,
    effective_to DATE NULL,
    content TEXT NOT NULL,
    retrieval_method TEXT NOT NULL,
    fused_score DOUBLE PRECISION NOT NULL,
    semantic_rank INTEGER NULL,
    lexical_rank INTEGER NULL,
    PRIMARY KEY (assessment_id, control_id, evidence_position),
    CHECK (semantic_rank IS NULL OR semantic_rank > 0),
    CHECK (lexical_rank IS NULL OR lexical_rank > 0),
    CHECK (effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from)
);

CREATE INDEX IF NOT EXISTS assessment_evidence_source_idx
    ON assessment_regulatory_evidence (source_id, document_version_id, article_reference);

CREATE TABLE IF NOT EXISTS assessment_audit_events (
    audit_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessment_runs(assessment_id),
    event_type TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    event_json JSONB NOT NULL,
    event_sha256 CHAR(64) NOT NULL,
    UNIQUE (assessment_id, idempotency_key)
);

CREATE INDEX IF NOT EXISTS assessment_audit_events_assessment_idx
    ON assessment_audit_events (assessment_id, audit_event_id);

CREATE OR REPLACE FUNCTION reject_assessment_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'assessment audit events are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS assessment_audit_events_append_only ON assessment_audit_events;
CREATE TRIGGER assessment_audit_events_append_only
    BEFORE UPDATE OR DELETE ON assessment_audit_events
    FOR EACH ROW EXECUTE FUNCTION reject_assessment_audit_mutation();
