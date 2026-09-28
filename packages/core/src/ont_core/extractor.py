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
from ont_core.repositories import (
    ExtractionRepository,
    LineageRepository,
    ObservationRepository,
    PostgresLineageRepository,
)
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
        observations: ObservationRepository,
        extractions: ExtractionRepository,
        lineage: LineageRepository,
        config: ExtractorConfig | None = None,
    ):
        self.adapter = adapter
        self.observations = observations
        self.extractions = extractions
        self.lineage = lineage
        self.config = config or ExtractorConfig()
        self._stop_event: asyncio.Event | None = None
        self._db_pool: asyncpg.Pool | None = None

    @classmethod
    async def create(
        cls,
        adapter: LLMAdapter,
        db_config: DatabaseConfig | None = None,
        extractor_config: ExtractorConfig | None = None,
        observations: ObservationRepository | None = None,
        extractions: ExtractionRepository | None = None,
        lineage: LineageRepository | None = None,
    ) -> Extractor:
        """Factory method that creates DB pool and default repositories."""
        db_cfg = db_config or DatabaseConfig()
        pool = await asyncpg.create_pool(db_cfg.database_url, min_size=1, max_size=10)

        obs_repo = observations or ObservationRepository(pool)
        ext_repo = extractions or ExtractionRepository(pool)
        lineage_repo = lineage or PostgresLineageRepository(pool)

        instance = cls(adapter, obs_repo, ext_repo, lineage_repo, extractor_config)
        instance._db_pool = pool
        return instance

    async def close(self) -> None:
        """Clean up resources."""
        if self._db_pool:
            await self._db_pool.close()
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

        obs = await self.observations.get_by_id(observation_id)

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
                note=obs.note_text,
                species=f"{obs.common_name} ({obs.scientific_name})",
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            # Determine status based on confidence
            needs_review = result.extraction_confidence < self.config.confidence_threshold
            extraction_status = "needs_review" if needs_review else "completed"
            obs_status = "needs_review" if needs_review else "completed"

            # Save extraction via repository
            extraction_id = await self.extractions.create(
                observation_id=observation_id,
                behaviors=result.behaviors,
                breeding_evidence=result.breeding_evidence,
                habitat_features=result.habitat_features,
                life_stages=result.life_stages,
                count_detail=result.count_detail,
                weather_conditions=result.weather_conditions,
                extraction_confidence=result.extraction_confidence,
                status=extraction_status,
            )

            # Record lineage event for audit trail
            await self.lineage.record_extracted(
                extraction_id=extraction_id,
                adapter=self.adapter.name,
                model=self.adapter.model_version,
                prompt=f"species={obs.common_name}, note={obs.note_text[:200]}...",
                response=result.model_dump_json(),
                latency_ms=latency_ms,
                worker_id=worker_id,
            )

            # Update observation status
            await self.observations.update_status(observation_id, obs_status)

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
            retry_count = obs.retry_count + 1
            max_retries_reached = retry_count >= self.config.max_retries

            new_status = "failed" if max_retries_reached else "pending"

            await self.observations.update_status(
                observation_id,
                new_status,
                retry_count=retry_count,
                error=error_msg[:500],
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

        # Claim batch via repository
        claimed_ids = await self.observations.claim_pending_batch(batch_size)

        if not claimed_ids:
            logger.debug(f"{log_prefix}No pending observations to process")
            return []

        logger.info(f"{log_prefix}Claimed {len(claimed_ids)} observations for processing")

        outcomes = []
        processed_ids = []
        for obs_id in claimed_ids:
            # Check if stop requested (for graceful shutdown)
            if self._stop_event and self._stop_event.is_set():
                logger.info(f"{log_prefix}Stop requested, finishing batch early")
                break
            outcome = await self.extract_one(obs_id, worker_id=worker_id)
            outcomes.append(outcome)
            processed_ids.append(obs_id)

        # Reset unprocessed observations back to pending (graceful shutdown cleanup)
        unprocessed_ids = [id for id in claimed_ids if id not in processed_ids]
        if unprocessed_ids:
            reset_count = await self.observations.reset_to_pending(unprocessed_ids)
            logger.info(f"{log_prefix}Reset {reset_count} unprocessed observations back to pending")

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
