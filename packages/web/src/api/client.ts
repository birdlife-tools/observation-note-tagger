import { config } from "../config";

export interface Extraction {
  id: string;
  observation_id: string;
  status: string;
  extraction_confidence: number;
  behaviors: Array<{ type: string; context?: string }> | null;
  breeding_evidence: {
    code: string;
    description: string;
    confidence: number;
  } | null;
  habitat_features: string[] | null;
  life_stages: string[] | null;
  note_text: string;
  common_name: string;
  scientific_name: string;
  validation_issues: Array<{
    field: string;
    value: string;
    reason: string;
    severity: string;
  }> | null;
}

export interface ExtractionListResponse {
  data: Extraction[];
  meta: {
    total: number;
    limit: number;
    offset: number;
  };
}

export interface Stats {
  extractions: Record<string, number>;
  observations: Record<string, number>;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async getExtractions(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ExtractionListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));

    const url = `${this.baseUrl}/extractions?${searchParams}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  async reviewExtraction(
    extractionId: string,
    action: "approve" | "reject",
    notes?: string
  ): Promise<void> {
    const response = await fetch(
      `${this.baseUrl}/extractions/${extractionId}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, notes }),
      }
    );
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
  }

  async getStats(): Promise<Stats> {
    const response = await fetch(`${this.baseUrl}/stats`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json();
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const api = new ApiClient(config.ontApiUrl);
