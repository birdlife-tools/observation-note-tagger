"""Ollama adapter for local LLM extraction."""

from __future__ import annotations

import json

import httpx

from ont_core.adapters.base import LLMAdapter
from ont_core.config import OllamaConfig
from ont_core.schemas import ExtractionResult

EXTRACTION_PROMPT = """\
You are an expert ornithologist. Extract structured data from this observation note.

Species: {species}
Note: {note}

Extract:
1. behaviors: List of observed behaviors (singing, foraging, feeding_young, etc.)
2. breeding_evidence: Any breeding codes (S=singing, FL=fledglings, FY=feeding young)
3. habitat_features: Mentioned habitat elements (forest_edge, dead_snag, etc.)
4. life_stages: Age classes mentioned (adult, juvenile, fledgling, etc.)
5. count_detail: Count breakdown by age/sex if mentioned
6. weather_conditions: Weather if mentioned

Respond ONLY with valid JSON matching this schema:
{{
  "behaviors": [{{"type": "singing", "context": "territorial"}}],
  "breeding_evidence": {{"code": "FL", "description": "...", "confidence": 0.9}},
  "habitat_features": ["forest_edge"],
  "life_stages": ["adult"],
  "count_detail": {{"adults": 2}},
  "weather_conditions": null,
  "extraction_confidence": 0.85
}}

If no data for a field, use empty list [] or null. Be conservative."""


class OllamaAdapter(LLMAdapter):
    """Ollama adapter for local LLM inference."""

    def __init__(self, config: OllamaConfig | None = None):
        cfg = config or OllamaConfig()
        self.base_url = cfg.base_url.rstrip("/")
        self.model = cfg.model
        self._client = httpx.AsyncClient(timeout=float(cfg.timeout))

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_version(self) -> str:
        return self.model

    async def extract(self, note: str, species: str) -> ExtractionResult:
        prompt = EXTRACTION_PROMPT.format(species=species, note=note)

        response = await self._client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
        )
        response.raise_for_status()

        result = response.json()
        raw_response = result.get("response", "{}")

        try:
            extracted = json.loads(raw_response)
        except json.JSONDecodeError:
            extracted = {}

        return ExtractionResult(
            behaviors=extracted.get("behaviors", []),
            breeding_evidence=extracted.get("breeding_evidence"),
            habitat_features=extracted.get("habitat_features", []),
            life_stages=extracted.get("life_stages", []),
            count_detail=extracted.get("count_detail"),
            weather_conditions=extracted.get("weather_conditions"),
            extraction_confidence=extracted.get("extraction_confidence", 0.0),
            raw_note=note,
        )

    async def close(self) -> None:
        await self._client.aclose()
