"""Tests for file parsers."""

import tempfile
from pathlib import Path

import pytest
from ont_core.parsers import EBirdParser, ParsedObservation


class TestEBirdParser:
    """Tests for the EBird parser."""

    @pytest.fixture
    def parser(self):
        return EBirdParser()

    @pytest.fixture
    def sample_ebd_file(self):
        """Create a minimal EBD file for testing."""
        # EBD header (52 columns, tab-separated)
        header = "\t".join([
            "GLOBAL UNIQUE IDENTIFIER",  # 0
            "LAST EDITED DATE",  # 1
            "TAXONOMIC ORDER",  # 2
            "CATEGORY",  # 3
            "TAXON CONCEPT ID",  # 4
            "COMMON NAME",  # 5
            "SCIENTIFIC NAME",  # 6
            "SUBSPECIES COMMON NAME",  # 7
            "SUBSPECIES SCIENTIFIC NAME",  # 8
            "EXOTIC CODE",  # 9
            "OBSERVATION COUNT",  # 10
            "BREEDING CODE",  # 11
            "BREEDING CATEGORY",  # 12
            "BEHAVIOR CODE",  # 13
            "AGE/SEX",  # 14
            "COUNTRY",  # 15
            "COUNTRY CODE",  # 16
            "STATE",  # 17
            "STATE CODE",  # 18
            "COUNTY",  # 19
            "COUNTY CODE",  # 20
            "IBA CODE",  # 21
            "BCR CODE",  # 22
            "USFWS CODE",  # 23
            "ATLAS BLOCK",  # 24
            "LOCALITY",  # 25
            "LOCALITY ID",  # 26
            "LOCALITY TYPE",  # 27
            "LATITUDE",  # 28
            "LONGITUDE",  # 29
            "OBSERVATION DATE",  # 30
            "TIME OBSERVATIONS STARTED",  # 31
            "OBSERVER ID",  # 32
            "OBSERVER ORCID ID",  # 33
            "SAMPLING EVENT IDENTIFIER",  # 34
            "OBSERVATION TYPE",  # 35
            "PROTOCOL NAME",  # 36
            "PROTOCOL CODE",  # 37
            "PROJECT NAMES",  # 38
            "PROJECT IDENTIFIERS",  # 39
            "DURATION MINUTES",  # 40
            "EFFORT DISTANCE KM",  # 41
            "EFFORT AREA HA",  # 42
            "NUMBER OBSERVERS",  # 43
            "ALL SPECIES REPORTED",  # 44
            "GROUP IDENTIFIER",  # 45
            "HAS MEDIA",  # 46
            "APPROVED",  # 47
            "REVIEWED",  # 48
            "REASON",  # 49
            "CHECKLIST COMMENTS",  # 50
            "SPECIES COMMENTS",  # 51
        ])

        # Row with note (should be parsed)
        row_with_note = "\t".join([
            "URN:CornellLabOfOrnithology:EBIRD:OBS123",  # 0
            "2026-01-01",  # 1
            "1234",  # 2
            "species",  # 3
            "avibase-ABC123",  # 4
            "Common Raven",  # 5
            "Corvus corax",  # 6
            "",  # 7
            "",  # 8
            "",  # 9
            "2",  # 10
            "S",  # 11
            "",  # 12
            "",  # 13
            "",  # 14
            "Sweden",  # 15
            "SE",  # 16
            "Stockholm",  # 17
            "SE-AB",  # 18
            "",  # 19
            "",  # 20
            "",  # 21
            "",  # 22
            "",  # 23
            "",  # 24
            "Djurgården",  # 25
            "",  # 26
            "",  # 27
            "59.3293",  # 28
            "18.0686",  # 29
            "2026-01-15",  # 30
            "08:30",  # 31
            "obsr123456",  # 32
            "",  # 33
            "S123456789",  # 34
            "",  # 35
            "",  # 36
            "",  # 37
            "",  # 38
            "",  # 39
            "",  # 40
            "",  # 41
            "",  # 42
            "",  # 43
            "",  # 44
            "",  # 45
            "",  # 46
            "",  # 47
            "",  # 48
            "",  # 49
            "",  # 50
            "Singing from treetop, likely territorial male",  # 51
        ])

        # Row without note (should be skipped)
        row_without_note = "\t".join([
            "URN:CornellLabOfOrnithology:EBIRD:OBS456",
            "2026-01-01",
            "1235",
            "species",
            "avibase-DEF456",
            "House Sparrow",
            "Passer domesticus",
            "", "", "",
            "5",
            "",
            "", "", "",
            "Sweden",
            "SE",
            "Stockholm",
            "SE-AB",
            "", "", "", "", "", "",
            "Central Park",
            "", "",
            "59.3294",
            "18.0687",
            "2026-01-15",
            "08:35",
            "obsr123456",
            "",
            "S123456790",
            "", "", "", "", "", "", "", "", "", "", "", "", "", "",
            "",  # Empty SPECIES COMMENTS
        ])

        content = f"{header}\n{row_with_note}\n{row_without_note}\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            return Path(f.name)

    def test_parser_properties(self, parser):
        assert parser.name == "ebird"
        assert parser.file_pattern == "ebd_*.txt"

    def test_validate_file(self, parser, sample_ebd_file):
        assert parser.validate_file(sample_ebd_file) is True

    def test_validate_invalid_file(self, parser):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("wrong,header,format\n")
            path = Path(f.name)
        assert parser.validate_file(path) is False

    def test_parse_yields_only_rows_with_notes(self, parser, sample_ebd_file):
        observations = list(parser.parse(sample_ebd_file))
        assert len(observations) == 1  # Only row with note

    def test_parse_extracts_correct_fields(self, parser, sample_ebd_file):
        observations = list(parser.parse(sample_ebd_file))
        obs = observations[0]

        assert isinstance(obs, ParsedObservation)
        assert obs.common_name == "Common Raven"
        assert obs.scientific_name == "Corvus corax"
        assert obs.note == "Singing from treetop, likely territorial male"
        assert obs.checklist_id == "S123456789"
        assert obs.country_code == "SE"
        assert obs.locality == "Djurgården"
        assert obs.observer_id == "obsr123456"
        assert obs.ebird_breeding_code == "S"
        assert str(obs.latitude) == "59.3293"
        assert str(obs.longitude) == "18.0686"
        assert obs.source_line == 2  # Header is line 1

    def test_count_rows(self, parser, sample_ebd_file):
        count = parser.count_rows(sample_ebd_file)
        assert count == 2  # Both data rows (excluding header)
