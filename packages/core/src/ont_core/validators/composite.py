"""Composite validator — chains multiple validators."""

from __future__ import annotations

from ont_core.schemas import ExtractionResult
from ont_core.validators.schemas import ValidationResult


class CompositeValidator:
    """
    Chains multiple validators together.

    All validators run; issues are merged. Result is invalid if any validator
    returns invalid. Suggested confidence is the minimum across all validators.
    """

    def __init__(self, validators: list) -> None:
        self.validators = validators

    def validate(self, result: ExtractionResult, note: str) -> ValidationResult:
        if not self.validators:
            return ValidationResult.valid()

        all_issues = []
        is_valid = True
        min_confidence: float | None = None

        for validator in self.validators:
            v_result = validator.validate(result, note)
            all_issues.extend(v_result.issues)
            if not v_result.is_valid:
                is_valid = False
            if v_result.suggested_confidence is not None:
                if min_confidence is None:
                    min_confidence = v_result.suggested_confidence
                else:
                    min_confidence = min(min_confidence, v_result.suggested_confidence)

        if is_valid:
            return ValidationResult.valid()

        return ValidationResult.invalid(all_issues, min_confidence)
