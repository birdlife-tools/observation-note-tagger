"""Repository protocols (interfaces) for dependency injection.

Code should depend on these protocols, not concrete implementations.
This allows swapping PostgreSQL for any other backend.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID


class ObservationRepository(Protocol):
    """Interface for observation data access."""

    async def get_by_id(self, observation_id: UUID): ...

    async def bulk_insert(self, observations: list, ingest_file_id: int) -> list[UUID]: ...

    async def claim_pending_batch(self, limit: int) -> list[UUID]: ...

    async def update_status(
        self,
        observation_id: UUID,
        status: str,
        retry_count: int | None = None,
        error: str | None = None,
    ) -> None: ...

    async def reset_to_pending(self, observation_ids: list[UUID]) -> int: ...

    async def count_by_status(self) -> dict[str, int]: ...


class ExtractionRepository(Protocol):
    """Interface for extraction data access."""

    async def create(
        self,
        observation_id: UUID,
        behaviors: list | None,
        breeding_evidence: object | None,
        habitat_features: list[str] | None,
        life_stages: list[str] | None,
        count_detail: dict | None,
        weather_conditions: str | None,
        extraction_confidence: float,
        status: str,
    ) -> UUID: ...

    async def get_by_id(self, extraction_id: UUID) -> dict | None: ...

    async def get_by_observation(self, observation_id: UUID) -> dict | None: ...

    async def list_for_review(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]: ...

    async def update_status(
        self,
        extraction_id: UUID,
        status: str,
        reviewed_by: str | None = None,
        review_notes: str | None = None,
    ) -> bool: ...

    async def count_by_status(self) -> dict[str, int]: ...


class LineageRepository(Protocol):
    """Interface for lineage/provenance tracking."""

    async def record_event(
        self,
        entity_type: str,
        entity_id: UUID,
        event_type: str,
        source_ref: dict,
        parent_event_id: UUID | None = None,
        created_by: str = "system",
    ) -> UUID: ...

    async def record_ingested(
        self,
        observation_id: UUID,
        file_path: str,
        line_number: int,
        worker_id: int | None = None,
    ) -> UUID: ...

    async def record_extracted(
        self,
        extraction_id: UUID,
        adapter: str,
        model: str,
        prompt: str,
        response: str,
        latency_ms: int,
        parent_event_id: UUID | None = None,
        worker_id: int | None = None,
        validation_issues: list[dict] | None = None,
    ) -> UUID: ...

    async def get_validation_issues(self, extraction_id: UUID) -> list[dict] | None: ...


class IngestFileRepository(Protocol):
    """Interface for ingest file tracking."""

    async def create(self, file_path: str, file_hash: str | None = None) -> int: ...

    async def get_by_path(self, file_path: str): ...

    async def get_by_id(self, file_id: int): ...

    async def claim_pending_batch(self, limit: int) -> list: ...

    async def update_progress(
        self,
        file_id: int,
        last_processed_line: int,
        rows_inserted: int,
        rows_failed: int,
        rows_skipped: int,
    ) -> None: ...

    async def mark_completed(
        self,
        file_id: int,
        rows_total: int,
        rows_inserted: int,
        rows_failed: int,
        rows_skipped: int,
    ) -> None: ...

    async def mark_failed(self, file_id: int, error_message: str, max_retries: int) -> bool: ...

    async def reset_to_pending(self, file_ids: list[int]) -> int: ...

    async def reset_stale(self, older_than_minutes: int) -> int: ...

    async def reset_for_force(self, file_path: str) -> int | None: ...

    async def count_by_status(self) -> dict[str, int]: ...

    async def get_stats(self) -> dict: ...


class IngestFailedRowRepository(Protocol):
    """Interface for ingest failed row tracking."""

    async def create(
        self,
        ingest_file_id: int,
        line_number: int,
        error_message: str,
        raw_content: str | None = None,
    ) -> int: ...

    async def get_pending_retry(
        self, ingest_file_id: int | None = None, limit: int = 100
    ) -> list: ...

    async def mark_permanent_failure(self, row_id: int) -> None: ...

    async def delete_for_file(self, ingest_file_id: int) -> int: ...

    async def count_by_status(self, ingest_file_id: int | None = None) -> dict[str, int]: ...
