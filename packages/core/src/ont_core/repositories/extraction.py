"""Repository for extraction operations."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from ont_core.repositories.base import BaseRepository


class ExtractionRepository(BaseRepository):
    """PostgreSQL repository for extractions."""

    async def create(
        self,
        observation_id: UUID,
        behaviors: list[Any] | None,
        breeding_evidence: Any | None,
        habitat_features: list[str] | None,
        life_stages: list[str] | None,
        count_detail: dict | None,
        weather_conditions: str | None,
        extraction_confidence: float,
        status: str,
    ) -> UUID:
        """
        Create a new extraction record.

        Returns the new extraction's UUID.
        """
        async with self.db.acquire() as conn:
            extraction_id = await conn.fetchval(
                """
                INSERT INTO extractions (
                    observation_id, behaviors, breeding_evidence, habitat_features,
                    life_stages, count_detail, weather_conditions,
                    extraction_confidence, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                observation_id,
                self._to_jsonb(behaviors),
                self._to_jsonb(breeding_evidence),
                self._to_jsonb(habitat_features),
                self._to_jsonb(life_stages),
                self._to_jsonb(count_detail),
                weather_conditions,
                extraction_confidence,
                status,
            )
            return extraction_id

    async def get_by_observation(self, observation_id: UUID) -> dict | None:
        """Get extraction for an observation."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, observation_id, behaviors, breeding_evidence,
                       habitat_features, life_stages, count_detail,
                       weather_conditions, extraction_confidence, status,
                       created_at, updated_at
                FROM extractions
                WHERE observation_id = $1
                """,
                observation_id,
            )
            if not row:
                return None
            return dict(row)

    async def update_status(
        self,
        extraction_id: UUID,
        status: str,
        reviewed_by: str | None = None,
        review_notes: str | None = None,
    ) -> None:
        """Update extraction status (e.g., after review)."""
        async with self.db.acquire() as conn:
            if reviewed_by:
                await conn.execute(
                    """
                    UPDATE extractions
                    SET status = $1, reviewed_by = $2, review_notes = $3,
                        reviewed_at = NOW(), updated_at = NOW()
                    WHERE id = $4
                    """,
                    status,
                    reviewed_by,
                    review_notes,
                    extraction_id,
                )
            else:
                await conn.execute(
                    """
                    UPDATE extractions
                    SET status = $1, updated_at = NOW()
                    WHERE id = $2
                    """,
                    status,
                    extraction_id,
                )

    async def count_by_status(self) -> dict[str, int]:
        """Get counts of extractions by status."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM extractions
                GROUP BY status
                """
            )
            return {row["status"]: row["count"] for row in rows}

    def _to_jsonb(self, value: Any) -> str | None:
        """Convert Python value to JSON string for JSONB column."""
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps([v.model_dump() if hasattr(v, "model_dump") else v for v in value])
        if hasattr(value, "model_dump"):
            return value.model_dump_json()
        return json.dumps(value)
