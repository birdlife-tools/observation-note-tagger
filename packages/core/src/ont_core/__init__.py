"""Core extraction engine and LLM adapters for observation-note-tagger."""

from ont_core.config import ClaudeConfig, OllamaConfig, OpenAIConfig
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
    "ExtractionResult",
    "OllamaConfig",
    "ClaudeConfig",
    "OpenAIConfig",
]
