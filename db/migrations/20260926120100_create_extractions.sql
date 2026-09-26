-- migrate:up
CREATE TABLE extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    observation_id UUID NOT NULL REFERENCES observations(id) ON DELETE CASCADE,

    -- Extracted structured data (matches Pydantic ExtractionResult)
    behaviors JSONB DEFAULT '[]',
    breeding_evidence JSONB,
    habitat_features JSONB DEFAULT '[]',
    life_stages JSONB DEFAULT '[]',
    count_detail JSONB,
    weather_conditions TEXT,

    -- Quality metrics
    extraction_confidence DECIMAL(3, 2) CHECK (
        extraction_confidence >= 0 AND extraction_confidence <= 1
    ),

    -- Review status
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'completed', 'needs_review', 'reviewed', 'rejected')
    ),
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,

    -- If corrected during review, store original
    original_extraction JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_extractions_observation ON extractions(observation_id);
CREATE INDEX idx_extractions_status ON extractions(status);
CREATE INDEX idx_extractions_confidence ON extractions(extraction_confidence);
CREATE INDEX idx_extractions_needs_review ON extractions(status) WHERE status = 'needs_review';

-- migrate:down
DROP TABLE extractions;
