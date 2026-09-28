"""Parser protocols (interfaces) for file parsing.

Parsers convert source files (EBD, CSV, etc.) into observation records.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Protocol


@dataclass
class ParsedObservation:
    """
    A single observation parsed from a source file.

    Contains the fields needed to INSERT into the observations table.
    """

    # Required fields
    note: str
    common_name: str
    scientific_name: str
    species_code: str
    observation_date: date
    checklist_id: str  # SAMPLING EVENT IDENTIFIER
    country_code: str

    # Optional fields
    observer_id: str | None = None
    locality: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    observation_count: str | None = None  # Can be "X" for presence
    state_code: str | None = None
    ebird_breeding_code: str | None = None

    # Source tracking
    source_line: int = 0


class Parser(Protocol):
    """
    Interface for file parsers.

    Implementations parse specific file formats (EBD, CSV, etc.)
    into ParsedObservation records.
    """

    @property
    def name(self) -> str:
        """Parser identifier (e.g., 'ebird', 'csv')."""
        ...

    @property
    def file_pattern(self) -> str:
        """Glob pattern for files this parser handles (e.g., 'ebd_*.txt')."""
        ...

    def validate_file(self, path: Path) -> bool:
        """
        Quick check: can this parser handle this file?

        Should check header/format without reading the whole file.
        """
        ...

    def parse(self, path: Path) -> Iterator[ParsedObservation]:
        """
        Parse file and yield observations one by one.

        Memory-efficient: yields records, never loads full file.
        Skips rows with empty notes.
        Sets source_line on each record for traceability.
        """
        ...

    def count_rows(self, path: Path) -> int:
        """
        Count total rows in file (for progress tracking).

        Should be fast — count lines without parsing.
        """
        ...
