-- migrate:up

-- Generic lineage/provenance tracking for all pipeline events.
-- Replaces extraction_audit with a unified system.
CREATE TABLE lineage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What entity this event is about
    entity_type VARCHAR(50) NOT NULL,  -- 'observation', 'extraction', etc.
    entity_id UUID NOT NULL,           -- loose FK (no constraint for flexibility)

    -- What happened
    event_type VARCHAR(50) NOT NULL,   -- 'ingested', 'extracted', 'validated', 'reviewed'

    -- Event details (schema depends on event_type)
    source_ref JSONB NOT NULL DEFAULT '{}',
    -- Examples:
    -- ingested:  {file: "ebd_GB_...", line: 1234}
    -- extracted: {adapter: "ollama", model: "qwen2.5:7b", prompt: "...", response: "...", latency_ms: 150}
    -- validated: {validator: "breeding_code", passed: true}
    -- reviewed:  {reviewer: "user@example.com", decision: "approved"}

    -- Event chain (for tracing: ingest → extract → validate)
    parent_event_id UUID REFERENCES lineage_events(id) ON DELETE SET NULL,

    -- Who/what created this event
    created_by VARCHAR(100) DEFAULT 'system',  -- 'system', 'worker-1', user email

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lineage_entity ON lineage_events(entity_type, entity_id);
CREATE INDEX idx_lineage_event_type ON lineage_events(event_type);
CREATE INDEX idx_lineage_parent ON lineage_events(parent_event_id) WHERE parent_event_id IS NOT NULL;
CREATE INDEX idx_lineage_created ON lineage_events(created_at);

-- Migrate existing extraction_audit data to lineage_events
INSERT INTO lineage_events (entity_type, entity_id, event_type, source_ref, created_by, created_at)
SELECT
    'extraction',
    extraction_id,
    'extracted',
    jsonb_build_object(
        'adapter', llm_adapter,
        'model', llm_model_version,
        'prompt', prompt_text,
        'response', raw_response,
        'latency_ms', latency_ms,
        'input_tokens', input_tokens,
        'output_tokens', output_tokens
    ),
    'system',
    created_at
FROM extraction_audit;

-- Drop the old table
DROP TABLE extraction_audit;

-- migrate:down

-- Recreate extraction_audit
CREATE TABLE extraction_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id) ON DELETE CASCADE,
    llm_adapter VARCHAR(50) NOT NULL,
    llm_model_version VARCHAR(100) NOT NULL,
    prompt_text TEXT NOT NULL,
    raw_response TEXT NOT NULL,
    latency_ms INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_extraction ON extraction_audit(extraction_id);
CREATE INDEX idx_audit_adapter ON extraction_audit(llm_adapter);
CREATE INDEX idx_audit_created ON extraction_audit(created_at);

-- Migrate data back
INSERT INTO extraction_audit (extraction_id, llm_adapter, llm_model_version, prompt_text, raw_response, latency_ms, input_tokens, output_tokens, created_at)
SELECT
    entity_id,
    source_ref->>'adapter',
    source_ref->>'model',
    source_ref->>'prompt',
    source_ref->>'response',
    (source_ref->>'latency_ms')::INTEGER,
    (source_ref->>'input_tokens')::INTEGER,
    (source_ref->>'output_tokens')::INTEGER,
    created_at
FROM lineage_events
WHERE entity_type = 'extraction' AND event_type = 'extracted';

DROP TABLE lineage_events;
