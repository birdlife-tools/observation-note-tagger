"""Tests for extraction validators."""

from ont_core.schemas import (
    Behavior,
    BreedingCode,
    BreedingEvidence,
    ExtractionResult,
)
from ont_core.validators import (
    CompositeValidator,
    IssueSeverity,
    TextGroundingValidator,
    ValidationResult,
)


def make_extraction(
    breeding_code: BreedingCode | None = None,
    breeding_desc: str | None = None,
    behaviors: list[Behavior] | None = None,
    confidence: float = 0.8,
    note: str = "test note",
) -> ExtractionResult:
    breeding = None
    if breeding_code:
        breeding = BreedingEvidence(
            code=breeding_code,
            description=breeding_desc or "test description",
            confidence=0.8,
        )
    return ExtractionResult(
        behaviors=behaviors or [],
        breeding_evidence=breeding,
        extraction_confidence=confidence,
        raw_note=note,
    )


class TestTextGroundingValidator:
    def test_valid_extraction_no_breeding(self):
        validator = TextGroundingValidator()
        result = make_extraction()
        validation = validator.validate(result, "Just a simple observation")
        assert validation.is_valid
        assert len(validation.issues) == 0

    def test_valid_breeding_with_keyword(self):
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="fledgling following adult",
        )
        validation = validator.validate(result, "Saw a fledgling following adult bird")
        assert validation.is_valid

    def test_false_positive_flew_to_FL(self):
        """The key hallucination case: 'flew over' should NOT be FL."""
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="flew over the field",
        )
        validation = validator.validate(result, "Single bird flew over the field")

        assert not validation.is_valid
        assert len(validation.issues) == 1
        issue = validation.issues[0]
        assert issue.field == "breeding_evidence.code"
        assert issue.value == "FL"
        assert issue.severity == IssueSeverity.ERROR
        assert "false positive" in issue.reason.lower()

    def test_false_positive_flying_to_FL(self):
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="flying overhead",
        )
        validation = validator.validate(result, "Bird was flying overhead")

        assert not validation.is_valid
        assert validation.issues[0].severity == IssueSeverity.ERROR

    def test_missing_keyword_warning(self):
        """Breeding code without supporting keywords is a warning."""
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FY,
            breeding_desc="at the nest",
        )
        validation = validator.validate(result, "Adult at the nest location")

        assert not validation.is_valid
        assert len(validation.issues) == 1
        assert validation.issues[0].severity == IssueSeverity.WARNING
        assert "feeding young" in validation.issues[0].reason.lower()

    def test_valid_FY_with_keyword(self):
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FY,
            breeding_desc="feeding young at nest",
        )
        validation = validator.validate(result, "Adult feeding young at nest box")
        assert validation.is_valid

    def test_valid_singing_code(self):
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.S,
            breeding_desc="singing from treetop",
        )
        validation = validator.validate(result, "Male was singing from the treetop")
        assert validation.is_valid

    def test_description_not_grounded(self):
        """Description that doesn't match note text."""
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.S,
            breeding_desc="elaborate courtship dance near water",
        )
        validation = validator.validate(result, "Bird was singing in the tree")

        assert not validation.is_valid
        issues = [i for i in validation.issues if i.field == "breeding_evidence.description"]
        assert len(issues) == 1
        assert "grounded" in issues[0].reason.lower()

    def test_confidence_adjustment_error(self):
        """Errors should significantly reduce confidence."""
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="flew over",
            confidence=0.9,
        )
        validation = validator.validate(result, "Bird flew over")

        assert validation.suggested_confidence is not None
        assert validation.suggested_confidence < 0.7  # Error penalty is 0.3

    def test_confidence_adjustment_warning(self):
        """Warnings should slightly reduce confidence."""
        validator = TextGroundingValidator()
        result = make_extraction(
            breeding_code=BreedingCode.CF,
            breeding_desc="unknown context",
            confidence=0.8,
        )
        validation = validator.validate(result, "Bird observed near bush")

        if not validation.is_valid and validation.suggested_confidence:
            assert validation.suggested_confidence >= 0.6  # Warning penalty is 0.1


class TestCompositeValidator:
    def test_empty_validators(self):
        composite = CompositeValidator([])
        result = make_extraction()
        validation = composite.validate(result, "test")
        assert validation.is_valid

    def test_single_validator(self):
        composite = CompositeValidator([TextGroundingValidator()])
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="flew over",
        )
        validation = composite.validate(result, "Bird flew over")
        assert not validation.is_valid

    def test_multiple_validators_merge_issues(self):
        class AlwaysWarningValidator:
            def validate(self, result, note):
                from ont_core.validators import ValidationIssue, ValidationResult

                return ValidationResult.invalid(
                    [
                        ValidationIssue(
                            field="test",
                            value="test",
                            reason="Always warns",
                            severity=IssueSeverity.WARNING,
                        )
                    ],
                    0.7,
                )

        composite = CompositeValidator(
            [
                TextGroundingValidator(),
                AlwaysWarningValidator(),
            ]
        )
        result = make_extraction(
            breeding_code=BreedingCode.FL,
            breeding_desc="flew over",
        )
        validation = composite.validate(result, "Bird flew over")

        assert not validation.is_valid
        assert len(validation.issues) >= 2


class TestValidationResult:
    def test_valid_factory(self):
        result = ValidationResult.valid()
        assert result.is_valid
        assert len(result.issues) == 0

    def test_has_errors(self):
        from ont_core.validators import ValidationIssue

        result = ValidationResult.invalid([ValidationIssue("f", "v", "r", IssueSeverity.ERROR)])
        assert result.has_errors
        assert not result.has_warnings

    def test_has_warnings(self):
        from ont_core.validators import ValidationIssue

        result = ValidationResult.invalid([ValidationIssue("f", "v", "r", IssueSeverity.WARNING)])
        assert not result.has_errors
        assert result.has_warnings

    def test_to_dict(self):
        from ont_core.validators import ValidationIssue

        result = ValidationResult.invalid(
            [ValidationIssue("field", "value", "reason", IssueSeverity.ERROR)], 0.5
        )
        d = result.to_dict()
        assert d["is_valid"] is False
        assert len(d["issues"]) == 1
        assert d["issues"][0]["field"] == "field"
        assert d["suggested_confidence"] == 0.5
