"""Validator protocols (interfaces) for dependency injection.

Code should depend on these protocols, not concrete implementations.
This allows swapping validation strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ont_core.schemas import ExtractionResult
    from ont_core.validators.schemas import ValidationResult


class Validator(Protocol):
    """Interface for extraction validators."""

    def validate(self, result: ExtractionResult, note: str) -> ValidationResult:
        """
        Validate an extraction result against the source note.

        Args:
            result: The extraction result from the LLM
            note: The original observation note text

        Returns:
            ValidationResult with is_valid flag and any issues found
        """
        ...
