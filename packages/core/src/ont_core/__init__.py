"""Core extraction engine and LLM adapters for observation-note-tagger."""

from ont_core.config import (
    ClaudeConfig,
    DatabaseConfig,
    ExtractorConfig,
    OllamaConfig,
    OpenAIConfig,
)
from ont_core.extractor import ExtractionOutcome, Extractor, RunStats
from ont_core.schemas import (
    Behavior,
    BehaviorType,
    BreedingCode,
    BreedingEvidence,
    ExtractionResult,
)

__all__ = [
    "Behavior",
    "BehaviorType",
    "BreedingCode",
    "BreedingEvidence",
    "ExtractionOutcome",
    "ExtractionResult",
    "Extractor",
    "RunStats",
    "ClaudeConfig",
    "DatabaseConfig",
    "ExtractorConfig",
    "OllamaConfig",
    "OpenAIConfig",
]
