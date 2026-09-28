"""Tests for Extractor and repository helper methods."""

import json

import pytest
from ont_core.repositories import (
    InMemoryLineageRepository,
    PostgresExtractionRepository,
)
from ont_core.schemas import Behavior, BehaviorType, BreedingCode, BreedingEvidence


class TestExtractionRepositoryJsonb:
    """Tests for the PostgresExtractionRepository._to_jsonb helper method."""

    @pytest.fixture
    def repo(self):
        """Create repository with mock pool for testing helpers."""

        class MockPool:
            pass

        return PostgresExtractionRepository(MockPool())

    def test_none_value(self, repo):
        assert repo._to_jsonb(None) is None

    def test_empty_list(self, repo):
        result = repo._to_jsonb([])
        assert result == "[]"

    def test_list_of_strings(self, repo):
        result = repo._to_jsonb(["forest_edge", "dead_snag"])
        parsed = json.loads(result)
        assert parsed == ["forest_edge", "dead_snag"]

    def test_list_of_pydantic_models(self, repo):
        behaviors = [
            Behavior(type=BehaviorType.SINGING, context="territorial"),
            Behavior(type=BehaviorType.FORAGING),
        ]
        result = repo._to_jsonb(behaviors)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["type"] == "singing"
        assert parsed[0]["context"] == "territorial"
        assert parsed[1]["type"] == "foraging"

    def test_pydantic_model(self, repo):
        evidence = BreedingEvidence(
            code=BreedingCode.FL, description="fledglings seen", confidence=0.9
        )
        result = repo._to_jsonb(evidence)
        parsed = json.loads(result)
        assert parsed["code"] == "FL"
        assert parsed["description"] == "fledglings seen"
        assert parsed["confidence"] == 0.9

    def test_dict(self, repo):
        count_detail = {"adults": 2, "juveniles": 3}
        result = repo._to_jsonb(count_detail)
        parsed = json.loads(result)
        assert parsed == {"adults": 2, "juveniles": 3}


class TestInMemoryLineageRepository:
    """Tests for the in-memory lineage repository."""

    @pytest.fixture
    def repo(self):
        return InMemoryLineageRepository()

    @pytest.mark.asyncio
    async def test_record_event(self, repo):
        from uuid import uuid4

        entity_id = uuid4()
        event_id = await repo.record_event(
            entity_type="test",
            entity_id=entity_id,
            event_type="created",
            source_ref={"foo": "bar"},
        )

        assert event_id is not None
        assert len(repo.events) == 1
        assert repo.events[0]["entity_type"] == "test"
        assert repo.events[0]["entity_id"] == entity_id
        assert repo.events[0]["event_type"] == "created"
        assert repo.events[0]["source_ref"] == {"foo": "bar"}

    @pytest.mark.asyncio
    async def test_find_by_entity(self, repo):
        from uuid import uuid4

        entity_id = uuid4()
        await repo.record_event(
            entity_type="observation",
            entity_id=entity_id,
            event_type="ingested",
            source_ref={"file": "test.txt", "line": 1},
        )
        await repo.record_event(
            entity_type="observation",
            entity_id=entity_id,
            event_type="extracted",
            source_ref={"adapter": "test"},
        )

        events = repo.find_by_entity("observation", entity_id)
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_clear(self, repo):
        from uuid import uuid4

        await repo.record_event(
            entity_type="test",
            entity_id=uuid4(),
            event_type="test",
            source_ref={},
        )
        assert len(repo.events) == 1

        repo.clear()
        assert len(repo.events) == 0
