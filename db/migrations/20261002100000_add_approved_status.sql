-- migrate:up
ALTER TABLE extractions DROP CONSTRAINT extractions_status_check;
ALTER TABLE extractions ADD CONSTRAINT extractions_status_check CHECK (
    status IN ('pending', 'completed', 'needs_review', 'reviewed', 'approved', 'rejected')
);

-- migrate:down
ALTER TABLE extractions DROP CONSTRAINT extractions_status_check;
ALTER TABLE extractions ADD CONSTRAINT extractions_status_check CHECK (
    status IN ('pending', 'completed', 'needs_review', 'reviewed', 'rejected')
);
