"""Ollama adapter for local LLM extraction."""

from __future__ import annotations

import json

import httpx

from ont_core.adapters.base import LLMAdapter
from ont_core.config import OllamaConfig
from ont_core.schemas import ExtractionResult

EXTRACTION_PROMPT = """\
You are an expert ornithologist. Extract ONLY what is explicitly stated in this note.

Species: {species}
Note: {note}

RULES - READ CAREFULLY:
1. Extract ONLY information explicitly written in the note
2. Do NOT infer or assume - if it's not stated, don't extract it
3. "flying over" or "flew" is NOT fledglings (FL) - FL means young birds just left nest
4. "heard call" is calling behavior, NOT singing
5. If unsure about breeding evidence, use null - do NOT guess

Breeding codes (use ONLY if clearly described):
- S: bird was singing (territorial song, not just calling)
- FL: fledglings explicitly mentioned (young birds recently left nest)
- FY: adult feeding young explicitly described
- CF: adult carrying food explicitly described
- CN: adult carrying nest material explicitly described

Respond with JSON:
{{
  "behaviors": [{{"type": "singing|calling|foraging|flying", "context": "..."}}],
  "breeding_evidence": null or {{"code": "XX", "description": "quote from note"}},
  "habitat_features": ["only if mentioned"],
  "life_stages": ["adult|juvenile|fledgling only if stated"],
  "count_detail": {{"adults": N}} or null,
  "weather_conditions": null or "quoted from note",
  "extraction_confidence": 0.9 if quoting note, 0.7 if slightly inferred, 0.5 if uncertain
}}

CRITICAL: breeding_evidence.description must be a direct quote or close paraphrase.
If the note just says "flew over" - that is NOT breeding evidence, use null."""


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

        # Handle empty objects as None (LLM sometimes returns {} instead of null)
        breeding_evidence = extracted.get("breeding_evidence")
        if breeding_evidence == {}:
            breeding_evidence = None

        count_detail = extracted.get("count_detail")
        if count_detail == {}:
            count_detail = None

        return ExtractionResult(
            behaviors=extracted.get("behaviors", []),
            breeding_evidence=breeding_evidence,
            habitat_features=extracted.get("habitat_features", []),
            life_stages=extracted.get("life_stages", []),
            count_detail=count_detail,
            weather_conditions=extracted.get("weather_conditions"),
            extraction_confidence=extracted.get("extraction_confidence", 0.5),
            raw_note=note,
        )

    async def close(self) -> None:
        await self._client.aclose()
