"""Extractor engine — core extraction loop for observation notes."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

import asyncpg

from ont_core.config import DatabaseConfig, ExtractorConfig
from ont_core.schemas import ExtractionResult

if TYPE_CHECKING:
    from ont_core.adapters.base import LLMAdapter

logger = logging.getLogger(__name__)


@dataclass
class ExtractionOutcome:
    """Result of a single extraction attempt."""

    observation_id: UUID
    success: bool
    extraction_id: UUID | None = None
    error: str | None = None
    needs_review: bool = False
    worker_id: int | None = None


@dataclass
class RunStats:
    """Statistics from a parallel extraction run."""

    total_processed: int = 0
    succeeded: int = 0
    failed: int = 0
    needs_review: int = 0
    workers_used: int = 0
    duration_seconds: float = 0.0
    outcomes: list[ExtractionOutcome] = field(default_factory=list)


class Extractor:
    """
    Production-ready extraction engine with parallel processing.

    Fetches pending observations, calls LLM adapter, saves results.
    Uses FOR UPDATE SKIP LOCKED for safe parallel worker execution.
    """

    def __init__(
        self,
        adapter: LLMAdapter,
        db_pool: asyncpg.Pool,
        config: ExtractorConfig | None = None,
    ):
        self.adapter = adapter
        self.db = db_pool
        self.config = config or ExtractorConfig()
        self._stop_event: asyncio.Event | None = None

    @classmethod
    async def create(
        cls,
        adapter: LLMAdapter,
        db_config: DatabaseConfig | None = None,
        extractor_config: ExtractorConfig | None = None,
    ) -> Extractor:
        """Factory method that creates DB pool."""
        db_cfg = db_config or DatabaseConfig()
        pool = await asyncpg.create_pool(db_cfg.database_url, min_size=1, max_size=10)
        return cls(adapter, pool, extractor_config)

    async def close(self) -> None:
        """Clean up resources."""
        await self.db.close()
        await self.adapter.close()

    async def extract_one(
        self, observation_id: UUID, worker_id: int | None = None
    ) -> ExtractionOutcome:
        """
        Extract structured data from a single observation.

        This is the core logic — unchanged between single/parallel mode.
        Handles: LLM call, result saving, audit logging, retry tracking.

        Note: Caller (run_batch) already set status='processing' atomically.
        """
        start_time = time.perf_counter()
        log_prefix = f"[worker-{worker_id}] " if worker_id is not None else ""

        async with self.db.acquire() as conn:
            # Fetch observation (already claimed as 'processing' by run_batch)
            obs = await conn.fetchrow(
                """
                SELECT id, species_code, common_name, scientific_name, note_text, retry_count
                FROM observations
                WHERE id = $1
                """,
                observation_id,
            )

            if not obs:
                logger.warning(f"{log_prefix}Observation {observation_id} not found")
                return ExtractionOutcome(
                    observation_id=observation_id,
                    success=False,
                    error="Not found",
                    worker_id=worker_id,
                )

            try:
                # Call LLM adapter
                result: ExtractionResult = await self.adapter.extract(
                    note=obs["note_text"],
                    species=f"{obs['common_name']} ({obs['scientific_name']})",
                )

                latency_ms = int((time.perf_counter() - start_time) * 1000)

                # Determine status based on confidence
                needs_review = result.extraction_confidence < self.config.confidence_threshold
                extraction_status = "needs_review" if needs_review else "completed"
                obs_status = "needs_review" if needs_review else "completed"

                # Save extraction
                extraction_id = await conn.fetchval(
                    """
                    INSERT INTO extractions (
                        observation_id, behaviors, breeding_evidence, habitat_features,
                        life_stages, count_detail, weather_conditions, extraction_confidence, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    observation_id,
                    self._to_jsonb(result.behaviors),
                    self._to_jsonb(result.breeding_evidence),
                    self._to_jsonb(result.habitat_features),
                    self._to_jsonb(result.life_stages),
                    self._to_jsonb(result.count_detail),
                    result.weather_conditions,
                    result.extraction_confidence,
                    extraction_status,
                )

                # Save audit record
                await conn.execute(
                    """
                    INSERT INTO extraction_audit (
                        extraction_id, llm_adapter, llm_model_version,
                        prompt_text, raw_response, latency_ms
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    extraction_id,
                    self.adapter.name,
                    self.adapter.model_version,
                    f"species={obs['common_name']}, note={obs['note_text'][:200]}...",
                    result.model_dump_json(),
                    latency_ms,
                )

                # Update observation status
                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = $1, retry_count = 0,
                        last_error = NULL, updated_at = NOW()
                    WHERE id = $2
                    """,
                    obs_status,
                    observation_id,
                )

                logger.info(
                    f"{log_prefix}Extracted {observation_id}: "
                    f"confidence={result.extraction_confidence:.2f}, "
                    f"behaviors={len(result.behaviors)}, latency={latency_ms}ms"
                )

                return ExtractionOutcome(
                    observation_id=observation_id,
                    success=True,
                    extraction_id=extraction_id,
                    needs_review=needs_review,
                    worker_id=worker_id,
                )

            except Exception as e:
                # Handle failure with retry tracking
                error_msg = str(e)
                retry_count = obs["retry_count"] + 1
                max_retries_reached = retry_count >= self.config.max_retries

                new_status = "failed" if max_retries_reached else "pending"

                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = $1, retry_count = $2,
                        last_error = $3, updated_at = NOW()
                    WHERE id = $4
                    """,
                    new_status,
                    retry_count,
                    error_msg[:500],
                    observation_id,
                )

                if max_retries_reached:
                    logger.error(
                        f"{log_prefix}Extraction failed permanently for {observation_id} "
                        f"after {retry_count} retries: {error_msg}"
                    )
                else:
                    logger.warning(
                        f"{log_prefix}Extraction failed for {observation_id} "
                        f"(retry {retry_count}/{self.config.max_retries}): {error_msg}"
                    )

                return ExtractionOutcome(
                    observation_id=observation_id,
                    success=False,
                    error=error_msg,
                    worker_id=worker_id,
                )

    async def run_batch(
        self, limit: int | None = None, worker_id: int | None = None
    ) -> list[ExtractionOutcome]:
        """
        Fetch and process a batch of pending observations.

        Uses atomic SELECT + UPDATE with FOR UPDATE SKIP LOCKED for safe
        parallel execution — multiple workers can call this simultaneously.
        """
        batch_size = limit or self.config.batch_size
        log_prefix = f"[worker-{worker_id}] " if worker_id is not None else ""

        async with self.db.acquire() as conn:
            # Atomic claim: SELECT + UPDATE in one query
            # FOR UPDATE SKIP LOCKED ensures parallel workers don't claim same rows
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
                batch_size,
            )

        if not rows:
            logger.debug(f"{log_prefix}No pending observations to process")
            return []

        logger.info(f"{log_prefix}Claimed {len(rows)} observations for processing")

        outcomes = []
        processed_ids = []
        for row in rows:
            # Check if stop requested (for graceful shutdown)
            if self._stop_event and self._stop_event.is_set():
                logger.info(f"{log_prefix}Stop requested, finishing batch early")
                break
            outcome = await self.extract_one(row["id"], worker_id=worker_id)
            outcomes.append(outcome)
            processed_ids.append(row["id"])

        # Reset unprocessed observations back to pending (graceful shutdown cleanup)
        all_ids = [row["id"] for row in rows]
        unprocessed_ids = [id for id in all_ids if id not in processed_ids]
        if unprocessed_ids:
            async with self.db.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE observations
                    SET extraction_status = 'pending', updated_at = NOW()
                    WHERE id = ANY($1) AND extraction_status = 'processing'
                    """,
                    unprocessed_ids,
                )
            logger.info(
                f"{log_prefix}Reset {len(unprocessed_ids)} unprocessed observations back to pending"
            )

        succeeded = sum(1 for o in outcomes if o.success)
        failed = sum(1 for o in outcomes if not o.success)
        needs_review = sum(1 for o in outcomes if o.needs_review)

        logger.info(
            f"{log_prefix}Batch complete: {succeeded} succeeded, {failed} failed, "
            f"{needs_review} need review"
        )

        return outcomes

    async def run_all(self) -> int:
        """Process all pending observations (single worker). Returns total processed."""
        total = 0
        while True:
            outcomes = await self.run_batch()
            if not outcomes:
                break
            total += len(outcomes)
        return total

    async def run_workers(self, num_workers: int | None = None) -> RunStats:
        """
        Run parallel extraction workers.

        Each worker continuously claims and processes batches until no more
        pending observations remain. Safe for concurrent execution via
        FOR UPDATE SKIP LOCKED.
        """
        workers = num_workers or self.config.parallel_workers
        self._stop_event = asyncio.Event()
        start_time = time.perf_counter()

        logger.info(f"Starting {workers} parallel extraction workers")

        all_outcomes: list[ExtractionOutcome] = []
        lock = asyncio.Lock()

        async def worker_loop(worker_id: int) -> None:
            while not self._stop_event.is_set():
                outcomes = await self.run_batch(worker_id=worker_id)
                if not outcomes:
                    break
                async with lock:
                    all_outcomes.extend(outcomes)

        # Run workers concurrently
        async with asyncio.TaskGroup() as tg:
            for i in range(workers):
                tg.create_task(worker_loop(i))

        duration = time.perf_counter() - start_time
        stats = RunStats(
            total_processed=len(all_outcomes),
            succeeded=sum(1 for o in all_outcomes if o.success),
            failed=sum(1 for o in all_outcomes if not o.success),
            needs_review=sum(1 for o in all_outcomes if o.needs_review),
            workers_used=workers,
            duration_seconds=duration,
            outcomes=all_outcomes,
        )

        logger.info(
            f"Parallel extraction complete: {stats.total_processed} processed "
            f"({stats.succeeded} ok, {stats.failed} failed, "
            f"{stats.needs_review} review) in {duration:.1f}s "
            f"with {workers} workers"
        )

        return stats

    def request_stop(self) -> None:
        """Request graceful shutdown of workers."""
        if self._stop_event:
            self._stop_event.set()

    def _to_jsonb(self, value) -> str | None:
        """Convert Pydantic model or list to JSON string for JSONB column."""
        if value is None:
            return None
        if isinstance(value, list):
            import json

            return json.dumps([v.model_dump() if hasattr(v, "model_dump") else v for v in value])
        if hasattr(value, "model_dump"):
            return value.model_dump_json()
        import json

        return json.dumps(value)
