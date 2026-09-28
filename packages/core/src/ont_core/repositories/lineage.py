"""Lineage/provenance tracking for pipeline events."""

from __future__ import annotations

import json
from typing import Protocol
from uuid import UUID, uuid4

from ont_core.repositories.base import BaseRepository


class LineageRepository(Protocol):
    """
    Interface for lineage/provenance storage.

    Implementations can use PostgreSQL, in-memory (for testing),
    or any other backend.
    """

    async def record_event(
        self,
        entity_type: str,
        entity_id: UUID,
        event_type: str,
        source_ref: dict,
        parent_event_id: UUID | None = None,
        created_by: str = "system",
    ) -> UUID:
        """Record a generic lineage event. Returns the event ID."""
        ...

    async def record_ingested(
        self,
        observation_id: UUID,
        file_path: str,
        line_number: int,
        worker_id: int | None = None,
    ) -> UUID:
        """Record an observation ingest event."""
        ...

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
    ) -> UUID:
        """Record an extraction event."""
        ...


class PostgresLineageRepository(BaseRepository):
    """PostgreSQL implementation of LineageRepository."""

    async def record_event(
        self,
        entity_type: str,
        entity_id: UUID,
        event_type: str,
        source_ref: dict,
        parent_event_id: UUID | None = None,
        created_by: str = "system",
    ) -> UUID:
        """Record a generic lineage event."""
        async with self.db.acquire() as conn:
            event_id = await conn.fetchval(
                """
                INSERT INTO lineage_events (
                    entity_type, entity_id, event_type, source_ref,
                    parent_event_id, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                entity_type,
                entity_id,
                event_type,
                json.dumps(source_ref),
                parent_event_id,
                created_by,
            )
            return event_id

    async def record_ingested(
        self,
        observation_id: UUID,
        file_path: str,
        line_number: int,
        worker_id: int | None = None,
    ) -> UUID:
        """Record an observation ingest event."""
        return await self.record_event(
            entity_type="observation",
            entity_id=observation_id,
            event_type="ingested",
            source_ref={
                "file": file_path,
                "line": line_number,
            },
            created_by=f"worker-{worker_id}" if worker_id is not None else "system",
        )

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
    ) -> UUID:
        """Record an extraction event."""
        return await self.record_event(
            entity_type="extraction",
            entity_id=extraction_id,
            event_type="extracted",
            source_ref={
                "adapter": adapter,
                "model": model,
                "prompt": prompt,
                "response": response,
                "latency_ms": latency_ms,
            },
            parent_event_id=parent_event_id,
            created_by=f"worker-{worker_id}" if worker_id is not None else "system",
        )


class InMemoryLineageRepository:
    """In-memory implementation for testing."""

    def __init__(self):
        self.events: list[dict] = []

    async def record_event(
        self,
        entity_type: str,
        entity_id: UUID,
        event_type: str,
        source_ref: dict,
        parent_event_id: UUID | None = None,
        created_by: str = "system",
    ) -> UUID:
        """Record a lineage event in memory."""
        event_id = uuid4()
        self.events.append(
            {
                "id": event_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "event_type": event_type,
                "source_ref": source_ref,
                "parent_event_id": parent_event_id,
                "created_by": created_by,
            }
        )
        return event_id

    async def record_ingested(
        self,
        observation_id: UUID,
        file_path: str,
        line_number: int,
        worker_id: int | None = None,
    ) -> UUID:
        """Record an observation ingest event."""
        return await self.record_event(
            entity_type="observation",
            entity_id=observation_id,
            event_type="ingested",
            source_ref={
                "file": file_path,
                "line": line_number,
            },
            created_by=f"worker-{worker_id}" if worker_id is not None else "system",
        )

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
    ) -> UUID:
        """Record an extraction event."""
        return await self.record_event(
            entity_type="extraction",
            entity_id=extraction_id,
            event_type="extracted",
            source_ref={
                "adapter": adapter,
                "model": model,
                "prompt": prompt,
                "response": response,
                "latency_ms": latency_ms,
            },
            parent_event_id=parent_event_id,
            created_by=f"worker-{worker_id}" if worker_id is not None else "system",
        )

    def clear(self) -> None:
        """Clear all events (useful in tests)."""
        self.events.clear()

    def find_by_entity(self, entity_type: str, entity_id: UUID) -> list[dict]:
        """Find all events for a given entity."""
        return [
            e
            for e in self.events
            if e["entity_type"] == entity_type and e["entity_id"] == entity_id
        ]
