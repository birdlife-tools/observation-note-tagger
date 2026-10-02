"""Repository for extraction operations."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from ont_core.repositories.base import BaseRepository


class PostgresExtractionRepository(BaseRepository):
    """PostgreSQL implementation of ExtractionRepository."""

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

    async def get_by_id(self, extraction_id: UUID) -> dict | None:
        """Get extraction by ID."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, observation_id, behaviors, breeding_evidence,
                       habitat_features, life_stages, count_detail,
                       weather_conditions, extraction_confidence, status,
                       created_at, updated_at
                FROM extractions
                WHERE id = $1
                """,
                extraction_id,
            )
            if not row:
                return None
            return dict(row)

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

    async def list_for_review(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """
        List extractions with observation data for review UI.

        Returns (list of extraction dicts, total count).
        """
        async with self.db.acquire() as conn:
            where_clause = "WHERE e.status = $1" if status else ""
            params: list = [status] if status else []

            query = f"""
                SELECT
                    e.id,
                    e.observation_id,
                    e.status,
                    e.extraction_confidence,
                    e.behaviors,
                    e.breeding_evidence,
                    e.habitat_features,
                    e.life_stages,
                    o.note_text,
                    o.common_name,
                    o.scientific_name
                FROM extractions e
                JOIN observations o ON e.observation_id = o.id
                {where_clause}
                ORDER BY e.created_at DESC
                LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
            params.extend([limit, offset])
            rows = await conn.fetch(query, *params)

            count_query = f"SELECT COUNT(*) FROM extractions e {where_clause}"
            if status:
                total = await conn.fetchval(count_query, status)
            else:
                total = await conn.fetchval(count_query)

            return [dict(row) for row in rows], total

    async def update_status(
        self,
        extraction_id: UUID,
        status: str,
        reviewed_by: str | None = None,
        review_notes: str | None = None,
    ) -> bool:
        """
        Update extraction and observation status (e.g., after review).

        Returns True if extraction was found and updated, False otherwise.
        """
        async with self.db.acquire() as conn:
            async with conn.transaction():
                if reviewed_by:
                    result = await conn.execute(
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
                    result = await conn.execute(
                        """
                        UPDATE extractions
                        SET status = $1, updated_at = NOW()
                        WHERE id = $2
                        """,
                        status,
                        extraction_id,
                    )

                if result == "UPDATE 0":
                    return False

                # Map extraction status to observation status
                # approved/rejected/completed → observation is "completed" (done processing)
                obs_status = (
                    "completed" if status in ("approved", "rejected", "completed") else status
                )

                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = $1, updated_at = NOW()
                    WHERE id = (SELECT observation_id FROM extractions WHERE id = $2)
                    """,
                    obs_status,
                    extraction_id,
                )
                return True

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
