export function ReviewQueue() {
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-lg font-semibold text-birdlife-text">
          Review Queue
        </h1>
        <p className="text-sm text-birdlife-muted">
          Extractions flagged for review due to low confidence or validation
          issues.
        </p>
      </div>

      <div className="bg-birdlife-card border border-birdlife-border rounded p-6">
        <p className="text-sm text-birdlife-muted">
          No extractions pending review.
        </p>
        <p className="text-xs text-birdlife-muted mt-2">
          API: GET /api/extractions?status=needs_review
        </p>
      </div>
    </div>
  );
}
