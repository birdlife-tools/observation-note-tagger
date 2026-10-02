import { useEffect, useState } from "react";
import { api, Stats } from "../api/client";

export function Statistics() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  const formatStatus = (status: string): string => {
    return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case "completed":
      case "approved":
        return "bg-green-100 text-green-800";
      case "needs_review":
        return "bg-yellow-100 text-yellow-800";
      case "failed":
      case "rejected":
        return "bg-red-100 text-red-800";
      case "pending":
        return "bg-gray-100 text-gray-800";
      case "processing":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-600";
    }
  };

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-lg font-semibold text-birdlife-text">
            Statistics
          </h1>
          <p className="text-sm text-birdlife-muted">
            Pipeline status overview
          </p>
        </div>
        <button
          onClick={loadStats}
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
      ) : stats ? (
        <div className="grid grid-cols-2 gap-6">
          <div className="bg-birdlife-card border border-birdlife-border rounded p-4">
            <h2 className="text-sm font-medium text-birdlife-muted mb-3">
              Observations
            </h2>
            <div className="space-y-2">
              {Object.entries(stats.observations).length === 0 ? (
                <p className="text-sm text-birdlife-muted">No data</p>
              ) : (
                Object.entries(stats.observations).map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${getStatusColor(status)}`}
                    >
                      {formatStatus(status)}
                    </span>
                    <span className="text-sm font-medium text-birdlife-text">
                      {count.toLocaleString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="bg-birdlife-card border border-birdlife-border rounded p-4">
            <h2 className="text-sm font-medium text-birdlife-muted mb-3">
              Extractions
            </h2>
            <div className="space-y-2">
              {Object.entries(stats.extractions).length === 0 ? (
                <p className="text-sm text-birdlife-muted">No data</p>
              ) : (
                Object.entries(stats.extractions).map(([status, count]) => (
                  <div key={status} className="flex justify-between items-center">
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${getStatusColor(status)}`}
                    >
                      {formatStatus(status)}
                    </span>
                    <span className="text-sm font-medium text-birdlife-text">
                      {count.toLocaleString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
