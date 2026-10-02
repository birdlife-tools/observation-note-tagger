"""Tests for Extractor and repository helper methods."""

import json
from uuid import uuid4

import pytest
from ont_core.config import ExtractorConfig
from ont_core.extractor import Extractor
from ont_core.repositories import (
    InMemoryLineageRepository,
    PostgresExtractionRepository,
)
from ont_core.schemas import (
    Behavior,
    BehaviorType,
    BreedingCode,
    BreedingEvidence,
    ExtractionResult,
)
from ont_core.validators import TextGroundingValidator


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
        await repo.record_event(
            entity_type="test",
            entity_id=uuid4(),
            event_type="test",
            source_ref={},
        )
        assert len(repo.events) == 1

        repo.clear()
        assert len(repo.events) == 0

    @pytest.mark.asyncio
    async def test_record_extracted_with_validation_issues(self, repo):
        extraction_id = uuid4()
        validation_issues = [
            {"field": "breeding_evidence.code", "value": "FL", "reason": "False positive"}
        ]

        event_id = await repo.record_extracted(
            extraction_id=extraction_id,
            adapter="ollama",
            model="test",
            prompt="test prompt",
            response="{}",
            latency_ms=100,
            validation_issues=validation_issues,
        )

        assert event_id is not None
        events = repo.find_by_entity("extraction", extraction_id)
        assert len(events) == 1
        assert events[0]["source_ref"]["validation_issues"] == validation_issues


class TestExtractorWithValidation:
    """Tests for Extractor with validator integration."""

    class MockObservation:
        def __init__(self, obs_id, note_text):
            self.id = obs_id
            self.note_text = note_text
            self.common_name = "European Robin"
            self.scientific_name = "Erithacus rubecula"
            self.retry_count = 0

    class MockObservationRepo:
        def __init__(self, observations: dict):
            self._obs = observations
            self.status_updates = []

        async def get_by_id(self, obs_id):
            return self._obs.get(obs_id)

        async def update_status(self, obs_id, status, retry_count=None, error=None):
            self.status_updates.append((obs_id, status, retry_count, error))

        async def claim_pending_batch(self, limit):
            return []

        async def reset_to_pending(self, obs_ids):
            return len(obs_ids)

    class MockExtractionRepo:
        def __init__(self):
            self.created = []

        async def create(self, **kwargs):
            extraction_id = uuid4()
            self.created.append({**kwargs, "id": extraction_id})
            return extraction_id

    class MockLLMAdapter:
        name = "mock"
        model_version = "test-1.0"

        def __init__(self, result: ExtractionResult):
            self._result = result

        async def extract(self, note: str, species: str) -> ExtractionResult:
            return self._result

        async def close(self):
            pass

    @pytest.mark.asyncio
    async def test_extraction_with_validation_flags_hallucination(self):
        """Validator catches 'flew over' → FL hallucination."""
        obs_id = uuid4()
        obs = self.MockObservation(obs_id, "Single bird flew over the field")

        llm_result = ExtractionResult(
            behaviors=[],
            breeding_evidence=BreedingEvidence(
                code=BreedingCode.FL,
                description="flew over the field",
                confidence=0.8,
            ),
            extraction_confidence=0.85,
            raw_note=obs.note_text,
        )

        obs_repo = self.MockObservationRepo({obs_id: obs})
        extraction_repo = self.MockExtractionRepo()
        lineage_repo = InMemoryLineageRepository()
        adapter = self.MockLLMAdapter(llm_result)
        validator = TextGroundingValidator()

        extractor = Extractor(
            adapter=adapter,
            observations=obs_repo,
            extractions=extraction_repo,
            lineage=lineage_repo,
            config=ExtractorConfig(confidence_threshold=0.7),
            validator=validator,
        )

        outcome = await extractor.extract_one(obs_id)

        assert outcome.success
        assert outcome.needs_review

        assert len(extraction_repo.created) == 1
        created = extraction_repo.created[0]
        assert created["status"] == "needs_review"
        assert created["extraction_confidence"] < 0.85

        events = lineage_repo.find_by_entity("extraction", outcome.extraction_id)
        assert len(events) == 1
        assert "validation_issues" in events[0]["source_ref"]
        issues = events[0]["source_ref"]["validation_issues"]
        assert len(issues) == 1
        assert issues[0]["field"] == "breeding_evidence.code"

    @pytest.mark.asyncio
    async def test_extraction_without_validator(self):
        """Extractor works fine without a validator."""
        obs_id = uuid4()
        obs = self.MockObservation(obs_id, "Bird singing in tree")

        llm_result = ExtractionResult(
            behaviors=[Behavior(type=BehaviorType.SINGING)],
            breeding_evidence=None,
            extraction_confidence=0.9,
            raw_note=obs.note_text,
        )

        obs_repo = self.MockObservationRepo({obs_id: obs})
        extraction_repo = self.MockExtractionRepo()
        lineage_repo = InMemoryLineageRepository()
        adapter = self.MockLLMAdapter(llm_result)

        extractor = Extractor(
            adapter=adapter,
            observations=obs_repo,
            extractions=extraction_repo,
            lineage=lineage_repo,
            validator=None,
        )

        outcome = await extractor.extract_one(obs_id)

        assert outcome.success
        assert not outcome.needs_review
        assert extraction_repo.created[0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_valid_extraction_passes_validation(self):
        """Valid extraction with real fledgling mention passes."""
        obs_id = uuid4()
        obs = self.MockObservation(obs_id, "Saw two fledglings being fed by adult")

        llm_result = ExtractionResult(
            behaviors=[],
            breeding_evidence=BreedingEvidence(
                code=BreedingCode.FL,
                description="fledglings being fed",
                confidence=0.9,
            ),
            extraction_confidence=0.9,
            raw_note=obs.note_text,
        )

        obs_repo = self.MockObservationRepo({obs_id: obs})
        extraction_repo = self.MockExtractionRepo()
        lineage_repo = InMemoryLineageRepository()
        adapter = self.MockLLMAdapter(llm_result)
        validator = TextGroundingValidator()

        extractor = Extractor(
            adapter=adapter,
            observations=obs_repo,
            extractions=extraction_repo,
            lineage=lineage_repo,
            validator=validator,
        )

        outcome = await extractor.extract_one(obs_id)

        assert outcome.success
        assert not outcome.needs_review
        assert extraction_repo.created[0]["status"] == "completed"

        events = lineage_repo.find_by_entity("extraction", outcome.extraction_id)
        assert "validation_issues" not in events[0]["source_ref"]
