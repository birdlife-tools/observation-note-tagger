"""Core extraction engine and LLM adapters for observation-note-tagger."""

from ont_core.config import (
    AppConfig,
    ClaudeConfig,
    DatabaseConfig,
    ExtractorConfig,
    OllamaConfig,
    OpenAIConfig,
)
from ont_core.extractor import ExtractionOutcome, Extractor, RunStats
from ont_core.factory import (
    RepositoryFactory,
    create_db_pool,
    create_extractor,
    create_extractor_with_repos,
    create_llm_adapter,
)
from ont_core.repositories import (
    # Implementations - use at composition root
    BaseRepository,
    # Protocols (interfaces) - depend on these
    ExtractionRepository,
    # Data records
    IngestFailedRowRecord,
    IngestFailedRowRepository,
    IngestFileRecord,
    IngestFileRepository,
    InMemoryLineageRepository,
    LineageRepository,
    ObservationRecord,
    ObservationRepository,
    PostgresExtractionRepository,
    PostgresIngestFailedRowRepository,
    PostgresIngestFileRepository,
    PostgresLineageRepository,
    PostgresObservationRepository,
)
from ont_core.schemas import (
    Behavior,
    BehaviorType,
    BreedingCode,
    BreedingEvidence,
    ExtractionResult,
)

__all__ = [
    # Protocols (interfaces)
    "ExtractionRepository",
    "IngestFailedRowRepository",
    "IngestFileRepository",
    "LineageRepository",
    "ObservationRepository",
    # Implementations
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
    # Factory (composition root)
    "RepositoryFactory",
    "create_db_pool",
    "create_extractor",
    "create_extractor_with_repos",
    "create_llm_adapter",
    # Extractor
    "ExtractionOutcome",
    "ExtractionResult",
    "Extractor",
    "RunStats",
    # Schemas
    "Behavior",
    "BehaviorType",
    "BreedingCode",
    "BreedingEvidence",
    # Config
    "AppConfig",
    "ClaudeConfig",
    "DatabaseConfig",
    "ExtractorConfig",
    "OllamaConfig",
    "OpenAIConfig",
]
