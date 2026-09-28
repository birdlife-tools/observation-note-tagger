"""Repository layer for database operations.

Protocols define the interfaces. Postgres* classes are the implementations.
Depend on protocols for injection, use implementations at composition root.
"""

from ont_core.repositories.base import BaseRepository
from ont_core.repositories.extraction import PostgresExtractionRepository
from ont_core.repositories.ingest import (
    IngestFailedRowRecord,
    IngestFileRecord,
    PostgresIngestFailedRowRepository,
    PostgresIngestFileRepository,
)
from ont_core.repositories.lineage import (
    InMemoryLineageRepository,
    PostgresLineageRepository,
)
from ont_core.repositories.observation import ObservationRecord, PostgresObservationRepository
from ont_core.repositories.protocols import (
    ExtractionRepository,
    IngestFailedRowRepository,
    IngestFileRepository,
    LineageRepository,
    ObservationRepository,
)

__all__ = [
    # Protocols (interfaces) - depend on these
    "ExtractionRepository",
    "IngestFailedRowRepository",
    "IngestFileRepository",
    "LineageRepository",
    "ObservationRepository",
    # Implementations - use at composition root
    "BaseRepository",
    "InMemoryLineageRepository",
    "PostgresExtractionRepository",
    "PostgresIngestFailedRowRepository",
    "PostgresIngestFileRepository",
    "PostgresLineageRepository",
    "PostgresObservationRepository",
    # Data records
    "IngestFailedRowRecord",
    "IngestFileRecord",
    "ObservationRecord",
]
