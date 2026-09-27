-- migrate:up
ALTER TABLE observations ADD COLUMN retry_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE observations ADD COLUMN last_error TEXT;

CREATE INDEX idx_observations_retry ON observations(retry_count) WHERE extraction_status = 'pending';

-- migrate:down
DROP INDEX IF EXISTS idx_observations_retry;
ALTER TABLE observations DROP COLUMN last_error;
ALTER TABLE observations DROP COLUMN retry_count;
