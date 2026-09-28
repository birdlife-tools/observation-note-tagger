-- migrate:up

-- ============================================================================
-- INGEST FILE TRACKING
-- ============================================================================

-- Track file-level ingest state for resumability
CREATE TABLE ingest_files (
    id SERIAL PRIMARY KEY,

    -- File identification (relative path for portability)
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT,  -- SHA256 for change detection

    -- Processing state
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'processing', 'completed', 'failed')
    ),

    -- Progress tracking
    rows_total INTEGER,           -- total rows in file (if known)
    rows_inserted INTEGER DEFAULT 0,
    rows_failed INTEGER DEFAULT 0,
    rows_skipped INTEGER DEFAULT 0,  -- empty notes
    last_processed_line INTEGER DEFAULT 0,  -- resumability checkpoint

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ingest_files_status ON ingest_files(status);
CREATE INDEX idx_ingest_files_retry ON ingest_files(retry_count) WHERE status = 'pending';

-- ============================================================================
-- INGEST FAILED ROWS
-- ============================================================================

-- Track row-level failures for retry
CREATE TABLE ingest_failed_rows (
    id SERIAL PRIMARY KEY,

    -- Which file this row belongs to
    ingest_file_id INTEGER NOT NULL REFERENCES ingest_files(id) ON DELETE CASCADE,

    -- Position and content
    line_number INTEGER NOT NULL,
    raw_content TEXT,  -- the problematic row data

    -- Error details
    error_message TEXT NOT NULL,

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'pending_retry' CHECK (
        status IN ('pending_retry', 'failed_permanent')
    ),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(ingest_file_id, line_number)
);

CREATE INDEX idx_failed_rows_file ON ingest_failed_rows(ingest_file_id);
CREATE INDEX idx_failed_rows_status ON ingest_failed_rows(status);

-- ============================================================================
-- OBSERVATIONS TABLE UPDATES FOR EBD COLUMNS
-- ============================================================================

-- Add ingest tracking (links observation to source file)
ALTER TABLE observations ADD COLUMN ingest_file_id INTEGER REFERENCES ingest_files(id);
ALTER TABLE observations ADD COLUMN source_line INTEGER;

-- Add eBird breeding code for comparison with our extraction
ALTER TABLE observations ADD COLUMN ebird_breeding_code VARCHAR(10);

CREATE INDEX idx_observations_ingest_file ON observations(ingest_file_id);

-- migrate:down

-- Remove observations columns
DROP INDEX IF EXISTS idx_observations_ingest_file;
ALTER TABLE observations DROP COLUMN IF EXISTS ebird_breeding_code;
ALTER TABLE observations DROP COLUMN IF EXISTS source_line;
ALTER TABLE observations DROP COLUMN IF EXISTS ingest_file_id;

-- Drop ingest tables
DROP TABLE IF EXISTS ingest_failed_rows;
DROP TABLE IF EXISTS ingest_files;
