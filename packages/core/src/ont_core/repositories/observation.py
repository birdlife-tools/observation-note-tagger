"""Repository for observation operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from ont_core.repositories.base import BaseRepository

if TYPE_CHECKING:
    from ont_core.parsers.protocols import ParsedObservation


@dataclass
class ObservationRecord:
    """Observation data from the database."""

    id: UUID
    species_code: str
    common_name: str
    scientific_name: str
    note_text: str
    retry_count: int
    extraction_status: str
    observation_date: date | None = None
    locality_name: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class PostgresObservationRepository(BaseRepository):
    """PostgreSQL implementation of ObservationRepository."""

    async def bulk_insert(
        self, observations: list[ParsedObservation], ingest_file_id: int
    ) -> list[UUID]:
        """
        Bulk insert observations from parsed records.

        Returns list of inserted observation IDs.
        Uses COPY for efficiency on large batches.
        """
        if not observations:
            return []

        async with self.db.acquire() as conn:
            # Use executemany for batch insert
            # Each row needs: sampling_event_id, species_code, common_name,
            # scientific_name, note_text, observation_date, country_code,
            # state_code, locality_name, latitude, longitude, observation_count,
            # observer_id, ingest_file_id, source_line, ebird_breeding_code
            ids = await conn.fetch(
                """
                INSERT INTO observations (
                    sampling_event_id, species_code, common_name, scientific_name,
                    note_text, observation_date, country_code, state_code,
                    locality_name, latitude, longitude, observation_count,
                    observer_id, ingest_file_id, source_line, ebird_breeding_code
                )
                SELECT
                    d.sampling_event_id, d.species_code, d.common_name,
                    d.scientific_name, d.note_text, d.observation_date::date,
                    d.country_code, d.state_code, d.locality_name,
                    d.latitude::decimal, d.longitude::decimal, d.observation_count,
                    d.observer_id, d.ingest_file_id::int, d.source_line::int,
                    d.ebird_breeding_code
                FROM unnest($1::text[], $2::text[], $3::text[], $4::text[],
                           $5::text[], $6::text[], $7::text[], $8::text[],
                           $9::text[], $10::text[], $11::text[], $12::text[],
                           $13::text[], $14::text[], $15::text[], $16::text[])
                AS d(sampling_event_id, species_code, common_name, scientific_name,
                     note_text, observation_date, country_code, state_code,
                     locality_name, latitude, longitude, observation_count,
                     observer_id, ingest_file_id, source_line, ebird_breeding_code)
                RETURNING id
                """,
                [o.checklist_id for o in observations],
                [o.species_code for o in observations],
                [o.common_name for o in observations],
                [o.scientific_name for o in observations],
                [o.note for o in observations],
                [str(o.observation_date) for o in observations],
                [o.country_code for o in observations],
                [o.state_code for o in observations],
                [o.locality for o in observations],
                [str(o.latitude) if o.latitude else None for o in observations],
                [str(o.longitude) if o.longitude else None for o in observations],
                [o.observation_count for o in observations],
                [o.observer_id for o in observations],
                [str(ingest_file_id) for _ in observations],
                [str(o.source_line) for o in observations],
                [o.ebird_breeding_code for o in observations],
            )
            return [row["id"] for row in ids]

    async def get_by_id(self, observation_id: UUID) -> ObservationRecord | None:
        """Fetch a single observation by ID."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, species_code, common_name, scientific_name, note_text,
                       retry_count, extraction_status, observation_date,
                       locality_name, latitude, longitude
                FROM observations
                WHERE id = $1
                """,
                observation_id,
            )
            if not row:
                return None
            return ObservationRecord(
                id=row["id"],
                species_code=row["species_code"],
                common_name=row["common_name"],
                scientific_name=row["scientific_name"],
                note_text=row["note_text"],
                retry_count=row["retry_count"],
                extraction_status=row["extraction_status"],
                observation_date=row["observation_date"],
                locality_name=row["locality_name"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            )

    async def claim_pending_batch(self, limit: int) -> list[UUID]:
        """
        Atomically claim a batch of pending observations for processing.

        Uses FOR UPDATE SKIP LOCKED for safe parallel worker execution.
        Returns list of claimed observation IDs.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                UPDATE observations
                SET extraction_status = 'processing', updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM observations
                    WHERE extraction_status = 'pending'
                    ORDER BY created_at
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id
                """,
                limit,
            )
            return [row["id"] for row in rows]

    async def update_status(
        self,
        observation_id: UUID,
        status: str,
        retry_count: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update observation extraction status."""
        async with self.db.acquire() as conn:
            if retry_count is not None:
                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = $1, retry_count = $2,
                        last_error = $3, updated_at = NOW()
                    WHERE id = $4
                    """,
                    status,
                    retry_count,
                    error,
                    observation_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = $1, retry_count = 0,
                        last_error = NULL, updated_at = NOW()
                    WHERE id = $2
                    """,
                    status,
                    observation_id,
                )

    async def reset_to_pending(self, observation_ids: list[UUID]) -> int:
        """
        Reset observations back to pending status.

        Used for graceful shutdown cleanup when processing was interrupted.
        Returns count of rows updated.
        """
        if not observation_ids:
            return 0
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE observations
                SET extraction_status = 'pending', updated_at = NOW()
                WHERE id = ANY($1) AND extraction_status = 'processing'
                """,
                observation_ids,
            )
            return int(result.split()[-1])

    async def count_by_status(self) -> dict[str, int]:
        """Get counts of observations by extraction status."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT extraction_status, COUNT(*) as count
                FROM observations
                GROUP BY extraction_status
                """
            )
            return {row["extraction_status"]: row["count"] for row in rows}
