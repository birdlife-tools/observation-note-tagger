"""Base adapter interface for LLM extraction."""

from abc import ABC, abstractmethod

from ont_core.schemas import ExtractionResult


class LLMAdapter(ABC):
    """Abstract base class for LLM adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Adapter name for audit logging."""
        ...

    @property
    @abstractmethod
    def model_version(self) -> str:
        """Model version string for audit logging."""
        ...

    @abstractmethod
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
