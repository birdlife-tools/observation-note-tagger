"""Tests for Ollama adapter with mocked HTTP responses."""

import json

import httpx
import pytest
from ont_core import OllamaConfig
from ont_core.adapters import OllamaAdapter


class TestOllamaAdapter:
    @pytest.fixture
    def adapter(self):
        return OllamaAdapter(OllamaConfig(base_url="http://test:11434"))

    def test_adapter_properties(self, adapter):
        assert adapter.name == "ollama"
        assert adapter.model_version == "qwen2.5:7b"

    @pytest.mark.asyncio
    async def test_extract_success(self, adapter, monkeypatch):
        mock_response = {
            "response": json.dumps(
                {
                    "behaviors": [{"type": "singing", "context": "territorial"}],
                    "breeding_evidence": {
                        "code": "S",
                        "description": "singing male",
                        "confidence": 0.9,
                    },
                    "habitat_features": ["oak_tree"],
                    "life_stages": ["adult"],
                    "count_detail": None,
                    "weather_conditions": None,
                    "extraction_confidence": 0.85,
                }
            )
        }

        async def mock_post(url, **kwargs):
            request = httpx.Request("POST", url)
            return httpx.Response(200, json=mock_response, request=request)

        monkeypatch.setattr(adapter._client, "post", mock_post)

        result = await adapter.extract(note="Singing male in oak tree", species="European Robin")

        assert len(result.behaviors) == 1
        assert result.behaviors[0].type.value == "singing"
        assert result.breeding_evidence.code.value == "S"
        assert result.extraction_confidence == 0.85
        assert result.raw_note == "Singing male in oak tree"

    @pytest.mark.asyncio
    async def test_extract_invalid_json(self, adapter, monkeypatch):
        mock_response = {"response": "not valid json"}

        async def mock_post(url, **kwargs):
            request = httpx.Request("POST", url)
            return httpx.Response(200, json=mock_response, request=request)

        monkeypatch.setattr(adapter._client, "post", mock_post)

        result = await adapter.extract(note="test", species="test")

        assert result.behaviors == []
        assert result.breeding_evidence is None
        assert result.extraction_confidence == 0.0

    @pytest.mark.asyncio
    async def test_close(self, adapter):
        await adapter.close()
