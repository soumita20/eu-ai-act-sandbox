CREATE TABLE IF NOT EXISTS human_review_decisions (
    review_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL REFERENCES assessment_runs(assessment_id),
    decision_sequence INTEGER NOT NULL CHECK (decision_sequence > 0),
    reviewer_id TEXT NOT NULL,
    finding_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (
        action IN ('ACCEPTED', 'REJECTED', 'NEEDS_ADDITIONAL_EVIDENCE', 'ESCALATED')
    ),
    comment TEXT NULL,
    supporting_evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    contradicting_evidence_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    change_reason TEXT NULL,
    idempotency_key TEXT NOT NULL,
    request_sha256 CHAR(64) NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    decision_json JSONB NOT NULL,
    decision_sha256 CHAR(64) NOT NULL,
    UNIQUE (assessment_id, decision_sequence),
    UNIQUE (assessment_id, idempotency_key),
    CHECK (jsonb_typeof(supporting_evidence_references) = 'array'),
    CHECK (jsonb_typeof(contradicting_evidence_references) = 'array')
);

CREATE INDEX IF NOT EXISTS human_review_assessment_idx
    ON human_review_decisions (assessment_id, decision_sequence DESC);

CREATE OR REPLACE FUNCTION reject_human_review_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'human review decisions are append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS human_review_decisions_append_only ON human_review_decisions;
CREATE TRIGGER human_review_decisions_append_only
    BEFORE UPDATE OR DELETE ON human_review_decisions
    FOR EACH ROW EXECUTE FUNCTION reject_human_review_mutation();
