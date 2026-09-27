"""Tests for Extractor helper methods."""

import json

import pytest

from ont_core.extractor import Extractor
from ont_core.schemas import Behavior, BehaviorType, BreedingCode, BreedingEvidence


class TestToJsonb:
    """Tests for the _to_jsonb helper method."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without DB/adapter for testing helpers."""

        class MockAdapter:
            pass

        class MockPool:
            pass

        return Extractor(adapter=MockAdapter(), db_pool=MockPool())

    def test_none_value(self, extractor):
        assert extractor._to_jsonb(None) is None

    def test_empty_list(self, extractor):
        result = extractor._to_jsonb([])
        assert result == "[]"

    def test_list_of_strings(self, extractor):
        result = extractor._to_jsonb(["forest_edge", "dead_snag"])
        parsed = json.loads(result)
        assert parsed == ["forest_edge", "dead_snag"]

    def test_list_of_pydantic_models(self, extractor):
        behaviors = [
            Behavior(type=BehaviorType.SINGING, context="territorial"),
            Behavior(type=BehaviorType.FORAGING),
        ]
        result = extractor._to_jsonb(behaviors)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["type"] == "singing"
        assert parsed[0]["context"] == "territorial"
        assert parsed[1]["type"] == "foraging"

    def test_pydantic_model(self, extractor):
        evidence = BreedingEvidence(
            code=BreedingCode.FL, description="fledglings seen", confidence=0.9
        )
        result = extractor._to_jsonb(evidence)
        parsed = json.loads(result)
        assert parsed["code"] == "FL"
        assert parsed["description"] == "fledglings seen"
        assert parsed["confidence"] == 0.9

    def test_dict(self, extractor):
        count_detail = {"adults": 2, "juveniles": 3}
        result = extractor._to_jsonb(count_detail)
        parsed = json.loads(result)
        assert parsed == {"adults": 2, "juveniles": 3}
