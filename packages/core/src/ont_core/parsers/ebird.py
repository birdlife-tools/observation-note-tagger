"""eBird Basic Dataset (EBD) parser.

Parses tab-separated EBD files into ParsedObservation records.
EBD files are downloaded from https://ebird.org/data/download
"""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ont_core.parsers.protocols import ParsedObservation

logger = logging.getLogger(__name__)


class EBirdParser:
    """
    Parser for eBird Basic Dataset (EBD) files.

    EBD files are tab-separated with a header row.
    This parser:
    - Streams rows (memory-efficient for large files)
    - Skips rows with empty SPECIES COMMENTS
    - Extracts the 10 columns we need for observations
    """

    # Column indices (0-based) in EBD file
    # Based on EBD format as of Aug 2026
    COL_GLOBAL_ID = 0
    COL_COMMON_NAME = 5
    COL_SCIENTIFIC_NAME = 6
    COL_OBSERVATION_COUNT = 10
    COL_BREEDING_CODE = 11
    COL_COUNTRY_CODE = 16
    COL_STATE_CODE = 18
    COL_LOCALITY = 25
    COL_LATITUDE = 28
    COL_LONGITUDE = 29
    COL_OBSERVATION_DATE = 30
    COL_OBSERVER_ID = 32
    COL_CHECKLIST_ID = 34  # SAMPLING EVENT IDENTIFIER
    COL_SPECIES_COMMENTS = 51
    COL_TAXON_CONCEPT_ID = 4  # Used as species_code

    # Expected header columns for validation
    EXPECTED_HEADERS = {
        COL_COMMON_NAME: "COMMON NAME",
        COL_SCIENTIFIC_NAME: "SCIENTIFIC NAME",
        COL_SPECIES_COMMENTS: "SPECIES COMMENTS",
        COL_CHECKLIST_ID: "SAMPLING EVENT IDENTIFIER",
    }

    @property
    def name(self) -> str:
        return "ebird"

    @property
    def file_pattern(self) -> str:
        return "ebd_*.txt"

    def validate_file(self, path: Path) -> bool:
        """Check if file has expected EBD header."""
        try:
            with open(path, encoding="utf-8") as f:
                header_line = f.readline()
                if not header_line:
                    return False

                headers = header_line.strip().split("\t")

                # Check key columns exist at expected positions
                for col_idx, expected_name in self.EXPECTED_HEADERS.items():
                    if col_idx >= len(headers):
                        logger.warning(
                            f"File {path.name} has only {len(headers)} columns, "
                            f"expected at least {col_idx + 1}"
                        )
                        return False
                    if headers[col_idx] != expected_name:
                        logger.warning(
                            f"File {path.name} column {col_idx} is '{headers[col_idx]}', "
                            f"expected '{expected_name}'"
                        )
                        return False

                return True
        except Exception as e:
            logger.warning(f"Failed to validate {path.name}: {e}")
            return False

    def parse(self, path: Path) -> Iterator[ParsedObservation]:
        """
        Parse EBD file and yield observations with non-empty notes.

        Streams the file line by line for memory efficiency.
        """
        with open(path, encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter="\t")

            # Skip header
            header = next(reader, None)
            if not header:
                return

            line_num = 1  # Header is line 1

            for row in reader:
                line_num += 1

                # Skip rows that are too short
                if len(row) <= self.COL_SPECIES_COMMENTS:
                    continue

                # Skip rows with empty notes (nothing to extract)
                note = row[self.COL_SPECIES_COMMENTS].strip()
                if not note:
                    continue

                try:
                    obs = self._parse_row(row, line_num)
                    if obs:
                        yield obs
                except Exception as e:
                    logger.warning(f"Failed to parse line {line_num} in {path.name}: {e}")
                    continue

    def _parse_row(self, row: list[str], line_num: int) -> ParsedObservation | None:
        """Parse a single row into a ParsedObservation."""
        # Required fields
        note = row[self.COL_SPECIES_COMMENTS].strip()
        common_name = row[self.COL_COMMON_NAME].strip()
        scientific_name = row[self.COL_SCIENTIFIC_NAME].strip()
        checklist_id = row[self.COL_CHECKLIST_ID].strip()
        country_code = row[self.COL_COUNTRY_CODE].strip()

        # Parse date
        date_str = row[self.COL_OBSERVATION_DATE].strip()
        try:
            observation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Invalid date '{date_str}' at line {line_num}")
            return None

        # Use TAXON CONCEPT ID as species code (truncate if needed)
        taxon_id = row[self.COL_TAXON_CONCEPT_ID].strip()
        species_code = taxon_id[:20] if taxon_id else scientific_name[:20]

        # Optional fields
        observer_id = row[self.COL_OBSERVER_ID].strip() or None
        locality = row[self.COL_LOCALITY].strip() or None
        state_code = row[self.COL_STATE_CODE].strip() or None
        observation_count = row[self.COL_OBSERVATION_COUNT].strip() or None
        ebird_breeding_code = row[self.COL_BREEDING_CODE].strip() or None

        # Parse coordinates
        latitude = self._parse_decimal(row[self.COL_LATITUDE])
        longitude = self._parse_decimal(row[self.COL_LONGITUDE])

        return ParsedObservation(
            note=note,
            common_name=common_name,
            scientific_name=scientific_name,
            species_code=species_code,
            observation_date=observation_date,
            checklist_id=checklist_id,
            country_code=country_code,
            observer_id=observer_id,
            locality=locality,
            latitude=latitude,
            longitude=longitude,
            observation_count=observation_count,
            state_code=state_code,
            ebird_breeding_code=ebird_breeding_code,
            source_line=line_num,
        )

    def _parse_decimal(self, value: str) -> Decimal | None:
        """Parse decimal value, returning None for empty/invalid."""
        value = value.strip()
        if not value:
            return None
        try:
            return Decimal(value)
        except InvalidOperation:
            return None

    def count_rows(self, path: Path) -> int:
        """Count lines in file (excluding header)."""
        count = 0
        with open(path, encoding="utf-8") as f:
            # Skip header
            next(f, None)
            for _ in f:
                count += 1
        return count
