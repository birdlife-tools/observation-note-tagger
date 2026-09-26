-- migrate:up
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- eBird identifiers
    sampling_event_id VARCHAR(50) NOT NULL,
    global_unique_id VARCHAR(100),

    -- Species info
    species_code VARCHAR(20) NOT NULL,
    common_name VARCHAR(200) NOT NULL,
    scientific_name VARCHAR(200) NOT NULL,

    -- The note we extract from
    note_text TEXT NOT NULL,

    -- Context
    observation_date DATE NOT NULL,
    country_code VARCHAR(10) NOT NULL,
    state_code VARCHAR(20),
    locality_name VARCHAR(500),
    latitude DECIMAL(9, 6),
    longitude DECIMAL(9, 6),

    -- Observation details
    observation_count VARCHAR(20),
    observer_id VARCHAR(50),

    -- Processing status
    extraction_status VARCHAR(20) DEFAULT 'pending' CHECK (
        extraction_status IN ('pending', 'processing', 'completed', 'failed', 'needs_review')
    ),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_observations_status ON observations(extraction_status);
CREATE INDEX idx_observations_species ON observations(species_code);
CREATE INDEX idx_observations_country ON observations(country_code);
CREATE INDEX idx_observations_date ON observations(observation_date);
CREATE UNIQUE INDEX idx_observations_global_id ON observations(global_unique_id) WHERE global_unique_id IS NOT NULL;

-- migrate:down
DROP TABLE observations;
