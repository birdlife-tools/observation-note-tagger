"""Ingest engine for loading EBD files into the database.

Orchestrates parallel file processing with checkpointing and lineage tracking.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ont_core.config import IngestConfig

if TYPE_CHECKING:
    from ont_core.parsers.protocols import Parser
    from ont_core.repositories.protocols import (
        IngestFailedRowRepository,
        IngestFileRepository,
        LineageRepository,
        ObservationRepository,
    )

logger = logging.getLogger(__name__)


@dataclass
class IngestStats:
    """Statistics from an ingest run."""

    files_found: int = 0
    files_processed: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    rows_inserted: int = 0
    rows_failed: int = 0
    rows_skipped: int = 0
    elapsed_seconds: float = 0.0


@dataclass
class IngestEngine:
    """
    Engine for ingesting EBD files into the database.

    Features:
    - Parallel file processing with configurable workers
    - Batch INSERT for efficiency (default 1000 rows)
    - Checkpointing for crash recovery
    - --force support for re-ingesting files
    - Lineage tracking for provenance
    """

    parser: Parser
    observation_repo: ObservationRepository
    file_repo: IngestFileRepository
    failed_row_repo: IngestFailedRowRepository
    lineage_repo: LineageRepository
    config: IngestConfig = field(default_factory=IngestConfig)

    _shutdown_requested: bool = field(default=False, init=False)
    _active_files: list[int] = field(default_factory=list, init=False)

    def __post_init__(self):
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown on SIGINT/SIGTERM."""
        logger.info("Shutdown requested, finishing current batch...")
        self._shutdown_requested = True

    async def run(
        self,
        directory: Path,
        workers: int = 1,
        force: bool = False,
        dry_run: bool = False,
    ) -> IngestStats:
        """
        Run the ingest process.

        Args:
            directory: Directory containing EBD files
            workers: Number of parallel workers (default 1)
            force: Re-ingest already completed files
            dry_run: Validate files without inserting

        Returns:
            Statistics from the run
        """
        import time

        start_time = time.time()
        stats = IngestStats()

        # Reset any stale processing files
        stale_count = await self.file_repo.reset_stale(self.config.stale_timeout_minutes)
        if stale_count:
            logger.info(f"Reset {stale_count} stale files to pending")

        # Discover files
        files = self._discover_files(directory)
        stats.files_found = len(files)

        if not files:
            logger.info(f"No files matching {self.parser.file_pattern} in {directory}")
            return stats

        logger.info(f"Found {len(files)} files matching {self.parser.file_pattern}")

        if dry_run:
            return await self._dry_run(files, stats)

        # Register files in database
        await self._register_files(files, force)

        # Process files with workers
        if workers == 1:
            await self._process_sequential(stats)
        else:
            await self._process_parallel(workers, stats)

        stats.elapsed_seconds = time.time() - start_time
        return stats

    def _discover_files(self, directory: Path) -> list[Path]:
        """Find files matching the parser's pattern."""
        pattern = self.parser.file_pattern
        files = sorted(directory.glob(pattern))
        return [f for f in files if f.is_file()]

    async def _register_files(self, files: list[Path], force: bool) -> None:
        """Register discovered files in the database."""
        for file_path in files:
            rel_path = str(file_path)
            existing = await self.file_repo.get_by_path(rel_path)

            if existing and existing.status == "completed":
                if force:
                    logger.info(f"Re-ingesting (--force): {file_path.name}")
                    await self.file_repo.reset_for_force(rel_path)
                    await self.failed_row_repo.delete_for_file(existing.id)
                else:
                    logger.debug(f"Skipping completed: {file_path.name}")
                    continue
            elif existing:
                logger.debug(f"Resuming: {file_path.name}")
            else:
                file_hash = self._compute_hash(file_path)
                await self.file_repo.create(rel_path, file_hash)
                logger.debug(f"Registered: {file_path.name}")

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file for change detection."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def _dry_run(self, files: list[Path], stats: IngestStats) -> IngestStats:
        """Validate files without inserting."""
        for file_path in files:
            if not self.parser.validate_file(file_path):
                logger.warning(f"INVALID: {file_path.name}")
                stats.files_failed += 1
                continue

            row_count = self.parser.count_rows(file_path)
            notes_count = sum(1 for _ in self.parser.parse(file_path))
            logger.info(f"VALID: {file_path.name} | {row_count} rows | {notes_count} with notes")
            stats.files_processed += 1
            stats.rows_inserted += notes_count
            stats.rows_skipped += row_count - notes_count

        return stats

    async def _process_sequential(self, stats: IngestStats) -> None:
        """Process files one at a time."""
        while not self._shutdown_requested:
            files = await self.file_repo.claim_pending_batch(1)
            if not files:
                break

            file_record = files[0]
            self._active_files = [file_record.id]

            try:
                file_stats = await self._process_file(file_record, worker_id=0)
                self._update_stats(stats, file_stats)
            finally:
                self._active_files = []

    async def _process_parallel(self, workers: int, stats: IngestStats) -> None:
        """Process files with multiple workers."""
        worker_stats = [IngestStats() for _ in range(workers)]
        tasks = [asyncio.create_task(self._worker(i, worker_stats[i])) for i in range(workers)]
        await asyncio.gather(*tasks)

        for ws in worker_stats:
            self._update_stats(stats, ws)

    async def _worker(self, worker_id: int, stats: IngestStats) -> None:
        """Worker coroutine that claims and processes files."""
        while not self._shutdown_requested:
            files = await self.file_repo.claim_pending_batch(1)
            if not files:
                break

            file_record = files[0]
            self._active_files.append(file_record.id)

            try:
                file_stats = await self._process_file(file_record, worker_id)
                self._update_stats(stats, file_stats)
            finally:
                if file_record.id in self._active_files:
                    self._active_files.remove(file_record.id)

    async def _process_file(self, file_record, worker_id: int) -> IngestStats:
        """Process a single file."""
        from ont_core.repositories.ingest import IngestFileRecord

        file_record: IngestFileRecord
        stats = IngestStats()
        file_path = Path(file_record.file_path)

        logger.info(f"[W{worker_id}] Processing: {file_path.name}")

        if not file_path.exists():
            await self.file_repo.mark_failed(
                file_record.id, f"File not found: {file_path}", self.config.max_retries
            )
            stats.files_failed += 1
            return stats

        if not self.parser.validate_file(file_path):
            await self.file_repo.mark_failed(
                file_record.id, "Invalid file format", self.config.max_retries
            )
            stats.files_failed += 1
            return stats

        try:
            batch: list = []
            rows_inserted = file_record.rows_inserted
            rows_failed = file_record.rows_failed
            rows_skipped = file_record.rows_skipped
            last_line = file_record.last_processed_line

            for obs in self.parser.parse(file_path):
                if self._shutdown_requested:
                    break

                # Skip already processed lines (resume support)
                if obs.source_line <= last_line:
                    continue

                batch.append(obs)

                if len(batch) >= self.config.batch_size:
                    inserted, failed = await self._insert_batch(batch, file_record.id, worker_id)
                    rows_inserted += inserted
                    rows_failed += failed
                    last_line = batch[-1].source_line
                    batch = []

                    # Checkpoint progress
                    await self.file_repo.update_progress(
                        file_record.id, last_line, rows_inserted, rows_failed, rows_skipped
                    )

            # Insert remaining batch
            if batch and not self._shutdown_requested:
                inserted, failed = await self._insert_batch(batch, file_record.id, worker_id)
                rows_inserted += inserted
                rows_failed += failed
                last_line = batch[-1].source_line

            if self._shutdown_requested:
                # Save progress for resume
                await self.file_repo.update_progress(
                    file_record.id, last_line, rows_inserted, rows_failed, rows_skipped
                )
                await self.file_repo.reset_to_pending([file_record.id])
                stats.files_skipped += 1
            else:
                # Count total rows for completion
                total_rows = self.parser.count_rows(file_path)
                rows_skipped = total_rows - rows_inserted - rows_failed

                await self.file_repo.mark_completed(
                    file_record.id, total_rows, rows_inserted, rows_failed, rows_skipped
                )
                stats.files_processed += 1

            stats.rows_inserted += rows_inserted
            stats.rows_failed += rows_failed
            stats.rows_skipped += rows_skipped

            logger.info(
                f"[W{worker_id}] Completed: {file_path.name} | "
                f"{rows_inserted} inserted, {rows_failed} failed, {rows_skipped} skipped"
            )

        except Exception as e:
            logger.exception(f"[W{worker_id}] Error processing {file_path.name}: {e}")
            permanent = await self.file_repo.mark_failed(
                file_record.id, str(e), self.config.max_retries
            )
            if permanent:
                stats.files_failed += 1
            else:
                logger.info(f"[W{worker_id}] Will retry: {file_path.name}")

        return stats

    async def _insert_batch(self, batch: list, file_id: int, worker_id: int) -> tuple[int, int]:
        """Insert a batch of observations. Returns (inserted, failed) counts."""
        try:
            ids = await self.observation_repo.bulk_insert(batch, file_id)

            # Record lineage for each inserted observation
            for obs, obs_id in zip(batch, ids):
                await self.lineage_repo.record_ingested(
                    observation_id=obs_id,
                    file_path=str(batch[0].checklist_id),  # Will be actual file path
                    line_number=obs.source_line,
                    worker_id=worker_id,
                )

            return len(ids), 0

        except Exception as e:
            logger.warning(f"Batch insert failed, falling back to row-by-row: {e}")
            return await self._insert_row_by_row(batch, file_id, worker_id)

    async def _insert_row_by_row(
        self, batch: list, file_id: int, worker_id: int
    ) -> tuple[int, int]:
        """Fallback: insert rows one by one, recording failures."""
        inserted = 0
        failed = 0

        for obs in batch:
            try:
                ids = await self.observation_repo.bulk_insert([obs], file_id)
                if ids:
                    await self.lineage_repo.record_ingested(
                        observation_id=ids[0],
                        file_path=str(obs.checklist_id),
                        line_number=obs.source_line,
                        worker_id=worker_id,
                    )
                    inserted += 1
            except Exception as e:
                await self.failed_row_repo.create(
                    ingest_file_id=file_id,
                    line_number=obs.source_line,
                    error_message=str(e),
                    raw_content=obs.note[:1000] if obs.note else None,
                )
                failed += 1

        return inserted, failed

    def _update_stats(self, total: IngestStats, delta: IngestStats) -> None:
        """Add delta stats to total."""
        total.files_processed += delta.files_processed
        total.files_skipped += delta.files_skipped
        total.files_failed += delta.files_failed
        total.rows_inserted += delta.rows_inserted
        total.rows_failed += delta.rows_failed
        total.rows_skipped += delta.rows_skipped

    async def cleanup(self) -> None:
        """Cleanup on shutdown - reset any active files."""
        if self._active_files:
            reset = await self.file_repo.reset_to_pending(self._active_files)
            logger.info(f"Reset {reset} active files to pending")
