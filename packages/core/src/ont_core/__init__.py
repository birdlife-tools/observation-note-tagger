"""Core extraction engine and LLM adapters for observation-note-tagger."""

from ont_core.config import (
    ClaudeConfig,
    DatabaseConfig,
    ExtractorConfig,
    OllamaConfig,
    OpenAIConfig,
)
from ont_core.extractor import ExtractionOutcome, Extractor, RunStats
from ont_core.repositories import (
    BaseRepository,
    ExtractionRepository,
    InMemoryLineageRepository,
    LineageRepository,
    ObservationRecord,
    ObservationRepository,
    PostgresLineageRepository,
)
from ont_core.schemas import (
    Behavior,
    BehaviorType,
    BreedingCode,
    BreedingEvidence,
    ExtractionResult,
)

__all__ = [
    "BaseRepository",
    "Behavior",
    "BehaviorType",
    "BreedingCode",
    "BreedingEvidence",
    "ExtractionOutcome",
    "ExtractionRepository",
    "ExtractionResult",
    "Extractor",
    "InMemoryLineageRepository",
    "LineageRepository",
    "ObservationRecord",
    "ObservationRepository",
    "PostgresLineageRepository",
    "RunStats",
    "ClaudeConfig",
    "DatabaseConfig",
    "ExtractorConfig",
    "OllamaConfig",
    "OpenAIConfig",
]
