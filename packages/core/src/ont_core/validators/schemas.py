"""Validation result schemas."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class IssueSeverity(StrEnum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    """A single validation issue found in an extraction."""

    field: str
    value: str
    reason: str
    severity: IssueSeverity = IssueSeverity.WARNING

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "reason": self.reason,
            "severity": self.severity.value,
        }


@dataclass
class ValidationResult:
    """Result of validating an extraction against source text."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    suggested_confidence: float | None = None

    @property
    def has_errors(self) -> bool:
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == IssueSeverity.WARNING for i in self.issues)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "suggested_confidence": self.suggested_confidence,
        }

    @classmethod
    def valid(cls) -> ValidationResult:
        """Factory for a valid result with no issues."""
        return cls(is_valid=True)

    @classmethod
    def invalid(
        cls, issues: list[ValidationIssue], suggested_confidence: float | None = None
    ) -> ValidationResult:
        """Factory for an invalid result."""
        return cls(
            is_valid=False,
            issues=issues,
            suggested_confidence=suggested_confidence,
        )
