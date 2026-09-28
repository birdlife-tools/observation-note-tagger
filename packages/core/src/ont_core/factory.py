"""Composition root — config-driven wiring of implementations.

Swap backends via environment variables (no code changes):
  ONT_REPO_BACKEND=postgres|memory
  ONT_LLM_ADAPTER=ollama|claude|openai

This is the ONLY module that imports concrete implementations.
Service layer (Extractor, Ingestor, etc.) depends only on Protocols.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from ont_core.config import (
    AppConfig,
    DatabaseConfig,
    ExtractorConfig,
    OllamaConfig,
)

if TYPE_CHECKING:
    from ont_core.adapters.base import LLMAdapter
    from ont_core.extractor import Extractor
    from ont_core.repositories import (
        ExtractionRepository,
        IngestFailedRowRepository,
        IngestFileRepository,
        LineageRepository,
        ObservationRepository,
    )


async def create_db_pool(config: DatabaseConfig | None = None) -> asyncpg.Pool:
    """Create a database connection pool."""
    cfg = config or DatabaseConfig()
    return await asyncpg.create_pool(cfg.database_url, min_size=1, max_size=10)


def create_llm_adapter(app_config: AppConfig | None = None) -> LLMAdapter:
    """
    Create LLM adapter based on config.

    Set via: ONT_LLM_ADAPTER=ollama|claude|openai
    """
    cfg = app_config or AppConfig()

    if cfg.llm_adapter == "ollama":
        from ont_core.adapters.ollama import OllamaAdapter

        return OllamaAdapter(OllamaConfig())

    elif cfg.llm_adapter == "claude":
        # Claude adapter not yet implemented
        raise NotImplementedError(
            "Claude adapter not yet implemented. "
            "Set ONT_LLM_ADAPTER=ollama or implement ClaudeAdapter."
        )

    elif cfg.llm_adapter == "openai":
        # OpenAI adapter not yet implemented
        raise NotImplementedError(
            "OpenAI adapter not yet implemented. "
            "Set ONT_LLM_ADAPTER=ollama or implement OpenAIAdapter."
        )

    else:
        raise ValueError(f"Unknown LLM adapter: {cfg.llm_adapter}")


class RepositoryFactory:
    """
    Creates repository instances based on config.

    Set via: ONT_REPO_BACKEND=postgres|memory
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool | None = None,
        app_config: AppConfig | None = None,
    ):
        self.db_pool = db_pool
        self.config = app_config or AppConfig()

        if self.config.repo_backend == "postgres" and not db_pool:
            raise ValueError("PostgreSQL backend requires a database pool")

    def observations(self) -> ObservationRepository:
        if self.config.repo_backend == "postgres":
            from ont_core.repositories import PostgresObservationRepository

            return PostgresObservationRepository(self.db_pool)
        else:
            raise NotImplementedError(
                "In-memory ObservationRepository not yet implemented. "
                "Set ONT_REPO_BACKEND=postgres."
            )

    def extractions(self) -> ExtractionRepository:
        if self.config.repo_backend == "postgres":
            from ont_core.repositories import PostgresExtractionRepository

            return PostgresExtractionRepository(self.db_pool)
        else:
            raise NotImplementedError(
                "In-memory ExtractionRepository not yet implemented. Set ONT_REPO_BACKEND=postgres."
            )

    def lineage(self) -> LineageRepository:
        if self.config.repo_backend == "postgres":
            from ont_core.repositories import PostgresLineageRepository

            return PostgresLineageRepository(self.db_pool)
        elif self.config.repo_backend == "memory":
            from ont_core.repositories import InMemoryLineageRepository

            return InMemoryLineageRepository()
        else:
            raise ValueError(f"Unknown repo backend: {self.config.repo_backend}")

    def ingest_files(self) -> IngestFileRepository:
        if self.config.repo_backend == "postgres":
            from ont_core.repositories import PostgresIngestFileRepository

            return PostgresIngestFileRepository(self.db_pool)
        else:
            raise NotImplementedError(
                "In-memory IngestFileRepository not yet implemented. Set ONT_REPO_BACKEND=postgres."
            )

    def ingest_failed_rows(self) -> IngestFailedRowRepository:
        if self.config.repo_backend == "postgres":
            from ont_core.repositories import PostgresIngestFailedRowRepository

            return PostgresIngestFailedRowRepository(self.db_pool)
        else:
            raise NotImplementedError(
                "In-memory IngestFailedRowRepository not yet implemented. "
                "Set ONT_REPO_BACKEND=postgres."
            )


async def create_extractor(
    adapter: LLMAdapter | None = None,
    db_config: DatabaseConfig | None = None,
    extractor_config: ExtractorConfig | None = None,
    app_config: AppConfig | None = None,
) -> Extractor:
    """
    Factory function to create a fully-wired Extractor.

    Backends determined by config:
      ONT_REPO_BACKEND=postgres|memory
      ONT_LLM_ADAPTER=ollama|claude|openai

    Or pass custom adapter/repositories for testing.
    """
    from ont_core.extractor import Extractor

    cfg = app_config or AppConfig()

    # Create or use provided adapter
    llm_adapter = adapter or create_llm_adapter(cfg)

    # Create DB pool if using postgres backend
    pool = None
    if cfg.repo_backend == "postgres":
        pool = await create_db_pool(db_config)

    # Create repositories via factory
    repo_factory = RepositoryFactory(pool, cfg)

    extractor = Extractor(
        adapter=llm_adapter,
        observations=repo_factory.observations(),
        extractions=repo_factory.extractions(),
        lineage=repo_factory.lineage(),
        config=extractor_config,
    )

    # Store pool reference for cleanup
    extractor._db_pool = pool
    return extractor


async def create_extractor_with_repos(
    adapter: LLMAdapter,
    observations: ObservationRepository,
    extractions: ExtractionRepository,
    lineage: LineageRepository,
    extractor_config: ExtractorConfig | None = None,
) -> Extractor:
    """
    Create Extractor with explicit repository instances.

    Use this for testing with mock/in-memory repositories.
    """
    from ont_core.extractor import Extractor

    return Extractor(
        adapter=adapter,
        observations=observations,
        extractions=extractions,
        lineage=lineage,
        config=extractor_config,
    )
