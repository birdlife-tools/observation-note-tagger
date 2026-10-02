import { useEffect, useState } from "react";
import { api, Extraction } from "../api/client";

export function ReviewQueue() {
  const [extractions, setExtractions] = useState<Extraction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const loadExtractions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getExtractions({ status: "needs_review" });
      setExtractions(response.data);
      setTotal(response.meta.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExtractions();
  }, []);

  const handleReview = async (id: string, action: "approve" | "reject") => {
    try {
      await api.reviewExtraction(id, action);
      setExtractions((prev) => prev.filter((e) => e.id !== id));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Review failed");
    }
  };

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-lg font-semibold text-birdlife-text">
            Review Queue
          </h1>
          <p className="text-sm text-birdlife-muted">
            {total} extraction{total !== 1 ? "s" : ""} pending review
          </p>
        </div>
        <button
          onClick={loadExtractions}
          className="text-sm text-birdlife-primary hover:text-birdlife-primary-hover"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-birdlife-muted">Loading...</div>
      ) : extractions.length === 0 ? (
        <div className="bg-birdlife-card border border-birdlife-border rounded p-6">
          <p className="text-sm text-birdlife-muted">
            No extractions pending review.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {extractions.map((extraction) => (
            <ExtractionCard
              key={extraction.id}
              extraction={extraction}
              onApprove={() => handleReview(extraction.id, "approve")}
              onReject={() => handleReview(extraction.id, "reject")}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface ExtractionCardProps {
  extraction: Extraction;
  onApprove: () => void;
  onReject: () => void;
}

function ExtractionCard({
  extraction,
  onApprove,
  onReject,
}: ExtractionCardProps) {
  return (
    <div className="bg-birdlife-card border border-birdlife-border rounded">
      <div className="p-4 border-b border-birdlife-border">
        <div className="flex justify-between items-start">
          <div>
            <span className="font-medium text-birdlife-text">
              {extraction.common_name}
            </span>
            <span className="ml-2 text-sm text-birdlife-muted italic">
              {extraction.scientific_name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                extraction.extraction_confidence < 0.5
                  ? "bg-red-100 text-red-700"
                  : extraction.extraction_confidence < 0.7
                    ? "bg-yellow-100 text-yellow-700"
                    : "bg-green-100 text-green-700"
              }`}
            >
              {(extraction.extraction_confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      <div className="p-4 grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs font-medium text-birdlife-muted mb-1">
            Original Note
          </div>
          <div className="text-sm text-birdlife-text bg-birdlife-bg p-2 rounded">
            {extraction.note_text}
          </div>
        </div>

        <div>
          <div className="text-xs font-medium text-birdlife-muted mb-1">
            Extraction
          </div>
          <div className="text-sm space-y-1">
            {extraction.breeding_evidence && (
              <div>
                <span className="text-birdlife-muted">Breeding:</span>{" "}
                <span className="font-mono bg-birdlife-bg px-1 rounded">
                  {extraction.breeding_evidence.code}
                </span>{" "}
                <span className="text-birdlife-muted">
                  {extraction.breeding_evidence.description}
                </span>
              </div>
            )}
            {extraction.behaviors && extraction.behaviors.length > 0 && (
              <div>
                <span className="text-birdlife-muted">Behaviors:</span>{" "}
                {extraction.behaviors.map((b, i) => (
                  <span key={i} className="font-mono bg-birdlife-bg px-1 rounded mr-1">
                    {b.type}
                  </span>
                ))}
              </div>
            )}
            {extraction.life_stages && extraction.life_stages.length > 0 && (
              <div>
                <span className="text-birdlife-muted">Life stages:</span>{" "}
                {extraction.life_stages.join(", ")}
              </div>
            )}
          </div>
        </div>
      </div>

      {extraction.validation_issues && extraction.validation_issues.length > 0 && (
        <div className="px-4 pb-4">
          <div className="text-xs font-medium text-red-600 mb-1">
            Validation Issues
          </div>
          <div className="space-y-1">
            {extraction.validation_issues.map((issue, i) => (
              <div
                key={i}
                className={`text-xs p-2 rounded ${
                  issue.severity === "error"
                    ? "bg-red-50 text-red-700"
                    : "bg-yellow-50 text-yellow-700"
                }`}
              >
                <span className="font-mono">{issue.field}</span>:{" "}
                {issue.reason}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="px-4 pb-4 flex gap-2 justify-end">
        <button
          onClick={onReject}
          className="px-3 py-1.5 text-sm border border-birdlife-border rounded hover:bg-birdlife-bg"
        >
          Reject
        </button>
        <button
          onClick={onApprove}
          className="px-3 py-1.5 text-sm bg-birdlife-primary text-white rounded hover:bg-birdlife-primary-hover"
        >
          Approve
        </button>
      </div>
    </div>
  );
}
