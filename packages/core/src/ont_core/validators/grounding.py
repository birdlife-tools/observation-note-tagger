"""Text grounding validator — checks extractions against source text."""

from __future__ import annotations

import re

from ont_core.schemas import BreedingCode, ExtractionResult
from ont_core.validators.schemas import IssueSeverity, ValidationIssue, ValidationResult

BREEDING_CODE_KEYWORDS: dict[BreedingCode, list[str]] = {
    BreedingCode.S: ["singing", "sang", "song", "territorial song"],
    BreedingCode.H: ["habitat", "suitable habitat", "appropriate habitat"],
    BreedingCode.P: ["pair", "paired", "mated pair", "couple"],
    BreedingCode.T: ["territory", "territorial", "defending territory"],
    BreedingCode.C: ["courtship", "courting", "display", "mating display"],
    BreedingCode.N: ["nest building", "building nest", "constructing nest"],
    BreedingCode.A: ["agitated", "alarm", "distraction display", "mobbing"],
    BreedingCode.B: ["eggs", "nest with eggs", "incubating"],
    BreedingCode.CN: ["carrying nest material", "carrying nesting material", "with nest material"],
    BreedingCode.CF: ["carrying food", "with food", "food in bill", "prey in bill"],
    BreedingCode.FY: ["feeding young", "fed young", "feeding chicks", "feeding nestlings"],
    BreedingCode.FL: ["fledgling", "fledglings", "fledged", "recently fledged", "just fledged"],
    BreedingCode.NY: ["nest with young", "nestlings", "young in nest", "chicks in nest"],
}

FALSE_POSITIVE_PATTERNS: dict[BreedingCode, list[str]] = {
    BreedingCode.FL: ["flew", "flying", "flight", "fly over", "flew over", "in flight"],
}


class TextGroundingValidator:
    """
    Validates that extractions are grounded in the source note text.

    Checks:
    - Breeding codes have supporting keywords in the note
    - Known false positive patterns are flagged (e.g., "flew" → FL)
    - Breeding evidence description appears in note
    """

    def validate(self, result: ExtractionResult, note: str) -> ValidationResult:
        issues: list[ValidationIssue] = []
        note_lower = note.lower()

        if result.breeding_evidence:
            issues.extend(self._validate_breeding_evidence(result, note_lower))

        if not issues:
            return ValidationResult.valid()

        suggested_confidence = self._calculate_adjusted_confidence(
            result.extraction_confidence, issues
        )

        return ValidationResult.invalid(issues, suggested_confidence)

    def _validate_breeding_evidence(
        self, result: ExtractionResult, note_lower: str
    ) -> list[ValidationIssue]:
        issues = []
        breeding = result.breeding_evidence
        if not breeding:
            return issues

        code = breeding.code

        if code in FALSE_POSITIVE_PATTERNS:
            for pattern in FALSE_POSITIVE_PATTERNS[code]:
                if pattern in note_lower:
                    has_valid_keyword = self._has_valid_keyword(code, note_lower)
                    if not has_valid_keyword:
                        keywords = BREEDING_CODE_KEYWORDS.get(code, [])
                        reason = (
                            f"Note contains '{pattern}' which is a false positive "
                            f"for {code.value}. Code {code.value} requires: "
                            f"{', '.join(keywords)}"
                        )
                        issues.append(
                            ValidationIssue(
                                field="breeding_evidence.code",
                                value=code.value,
                                reason=reason,
                                severity=IssueSeverity.ERROR,
                            )
                        )
                        break

        if not issues and code in BREEDING_CODE_KEYWORDS:
            if not self._has_valid_keyword(code, note_lower):
                issues.append(
                    ValidationIssue(
                        field="breeding_evidence.code",
                        value=code.value,
                        reason=f"No supporting keywords found for {code.value}. "
                        f"Expected one of: {', '.join(BREEDING_CODE_KEYWORDS[code])}",
                        severity=IssueSeverity.WARNING,
                    )
                )

        if breeding.description:
            desc_words = self._extract_significant_words(breeding.description)
            note_words = set(note_lower.split())
            overlap = desc_words & note_words
            if len(overlap) < len(desc_words) * 0.3:
                issues.append(
                    ValidationIssue(
                        field="breeding_evidence.description",
                        value=breeding.description[:50],
                        reason="Description does not appear to be grounded in note text",
                        severity=IssueSeverity.WARNING,
                    )
                )

        return issues

    def _has_valid_keyword(self, code: BreedingCode, note_lower: str) -> bool:
        keywords = BREEDING_CODE_KEYWORDS.get(code, [])
        return any(kw in note_lower for kw in keywords)

    def _extract_significant_words(self, text: str) -> set[str]:
        stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or", "with"}
        words = re.findall(r"\b[a-z]+\b", text.lower())
        return {w for w in words if w not in stopwords and len(w) > 2}

    def _calculate_adjusted_confidence(
        self, original: float, issues: list[ValidationIssue]
    ) -> float:
        penalty = 0.0
        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                penalty += 0.3
            else:
                penalty += 0.1
        return max(0.1, original - penalty)
