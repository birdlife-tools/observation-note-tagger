"""LLM adapter protocols (interfaces) for dependency injection.

Code should depend on these protocols, not concrete implementations.
This allows swapping LLM backends (Ollama, Claude, OpenAI) via config.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ont_core.schemas import ExtractionResult


class LLMAdapter(Protocol):
    """Interface for LLM extraction adapters."""

    @property
    def name(self) -> str:
        """Adapter name for audit logging (e.g., 'ollama', 'claude')."""
        ...

    @property
    def model_version(self) -> str:
        """Model version string for audit logging (e.g., 'qwen2.5:7b')."""
        ...

    async def extract(self, note: str, species: str) -> ExtractionResult:
        """
        Extract structured data from an observation note.

        Args:
            note: Raw observation note text
            species: Species common or scientific name for context

        Returns:
            ExtractionResult with extracted behaviors, breeding evidence, etc.
        """
        ...
