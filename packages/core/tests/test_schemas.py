"""Tests for Pydantic schemas."""

import pytest
from ont_core import Behavior, BehaviorType, BreedingCode, BreedingEvidence, ExtractionResult
from pydantic import ValidationError


class TestBehavior:
    def test_valid_behavior(self):
        b = Behavior(type=BehaviorType.SINGING, context="territorial")
        assert b.type == BehaviorType.SINGING
        assert b.context == "territorial"

    def test_behavior_minimal(self):
        b = Behavior(type=BehaviorType.FORAGING)
        assert b.type == BehaviorType.FORAGING
        assert b.context is None
        assert b.target_species is None

    def test_invalid_behavior_type(self):
        with pytest.raises(ValidationError):
            Behavior(type="invalid_type")


class TestBreedingEvidence:
    def test_valid_breeding_evidence(self):
        be = BreedingEvidence(code=BreedingCode.FL, description="fledglings seen", confidence=0.9)
        assert be.code == BreedingCode.FL
        assert be.confidence == 0.9

    def test_confidence_bounds(self):
        with pytest.raises(ValidationError):
            BreedingEvidence(code=BreedingCode.S, description="singing", confidence=1.5)

        with pytest.raises(ValidationError):
            BreedingEvidence(code=BreedingCode.S, description="singing", confidence=-0.1)


class TestExtractionResult:
    def test_minimal_extraction(self):
        result = ExtractionResult(extraction_confidence=0.8, raw_note="test note")
        assert result.behaviors == []
        assert result.breeding_evidence is None
        assert result.habitat_features == []

    def test_full_extraction(self):
        result = ExtractionResult(
            behaviors=[Behavior(type=BehaviorType.SINGING, context="dawn chorus")],
            breeding_evidence=BreedingEvidence(
                code=BreedingCode.FY, description="feeding young", confidence=0.95
            ),
            habitat_features=["forest_edge", "dead_snag"],
            life_stages=["adult", "juvenile"],
            count_detail={"adults": 2, "juveniles": 3},
            extraction_confidence=0.9,
            raw_note="2 adults feeding 3 juveniles at forest edge",
        )
        assert len(result.behaviors) == 1
        assert result.breeding_evidence.code == BreedingCode.FY
        assert "forest_edge" in result.habitat_features
