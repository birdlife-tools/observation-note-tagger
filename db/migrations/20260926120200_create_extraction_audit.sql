-- migrate:up
CREATE TABLE extraction_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,

    -- LLM details for reproducibility
    llm_adapter VARCHAR(50) NOT NULL,
    llm_model_version VARCHAR(100) NOT NULL,

    -- Full request/response for debugging
    prompt_text TEXT NOT NULL,
    raw_response TEXT NOT NULL,

    -- Performance metrics
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_extraction ON extraction_audit(extraction_id);
CREATE INDEX idx_audit_adapter ON extraction_audit(llm_adapter);
CREATE INDEX idx_audit_created ON extraction_audit(created_at);

-- migrate:down
DROP TABLE extraction_audit;
