"""Pydantic schemas for extraction results."""

from enum import StrEnum

from pydantic import BaseModel, Field


class BehaviorType(StrEnum):
    """Standard bird behavior categories."""

    SINGING = "singing"
    CALLING = "calling"
    FORAGING = "foraging"
    FEEDING_YOUNG = "feeding_young"
    NEST_BUILDING = "nest_building"
    COURTSHIP = "courtship"
    TERRITORIAL = "territorial"
    MIGRATION = "migration"
    ROOSTING = "roosting"
    BATHING = "bathing"
    PREENING = "preening"
    FLYING = "flying"
    PERCHING = "perching"
    OTHER = "other"


class BreedingCode(StrEnum):
    """eBird breeding codes."""

    S = "S"  # Singing
    H = "H"  # In appropriate habitat
    P = "P"  # Pair
    T = "T"  # Territory
    C = "C"  # Courtship
    N = "N"  # Nest building
    A = "A"  # Agitated behavior
    B = "B"  # Nest with eggs
    CN = "CN"  # Carrying nest material
    CF = "CF"  # Carrying food
    FY = "FY"  # Feeding young
    FL = "FL"  # Fledglings
    NY = "NY"  # Nest with young


class Behavior(BaseModel):
    """A single observed behavior."""

    type: BehaviorType
    context: str | None = None
    target_species: str | None = Field(default=None, description="For predation/feeding events")


class BreedingEvidence(BaseModel):
    """Breeding evidence extracted from observation."""

    code: BreedingCode
    description: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    """Structured data extracted from an observation note."""

    behaviors: list[Behavior] = Field(default_factory=list)
    breeding_evidence: BreedingEvidence | None = None
    habitat_features: list[str] = Field(default_factory=list)
    life_stages: list[str] = Field(default_factory=list, description="adult, juvenile, fledgling")
    count_detail: dict[str, int] | None = Field(
        default=None, description="Breakdown by age/sex if mentioned"
    )
    weather_conditions: str | None = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    raw_note: str = Field(description="Original note text")
