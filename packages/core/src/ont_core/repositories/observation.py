"""Repository for observation operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from ont_core.repositories.base import BaseRepository


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


class ObservationRepository(BaseRepository):
    """PostgreSQL repository for observations."""

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
