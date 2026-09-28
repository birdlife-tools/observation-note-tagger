"""Repository for ingest file and failed row operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ont_core.repositories.base import BaseRepository


@dataclass
class IngestFileRecord:
    """Ingest file data from the database."""

    id: int
    file_path: str
    file_hash: str | None
    status: str
    rows_total: int | None
    rows_inserted: int
    rows_failed: int
    rows_skipped: int
    last_processed_line: int
    retry_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class IngestFailedRowRecord:
    """Failed row data from the database."""

    id: int
    ingest_file_id: int
    line_number: int
    raw_content: str | None
    error_message: str
    retry_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class PostgresIngestFileRepository(BaseRepository):
    """PostgreSQL implementation of IngestFileRepository."""

    async def create(self, file_path: str, file_hash: str | None = None) -> int:
        """Create a new ingest file record. Returns the file ID."""
        async with self.db.acquire() as conn:
            file_id = await conn.fetchval(
                """
                INSERT INTO ingest_files (file_path, file_hash, status)
                VALUES ($1, $2, 'pending')
                ON CONFLICT (file_path) DO UPDATE SET
                    file_hash = EXCLUDED.file_hash,
                    updated_at = NOW()
                RETURNING id
                """,
                file_path,
                file_hash,
            )
            return file_id

    async def get_by_path(self, file_path: str) -> IngestFileRecord | None:
        """Get ingest file by path."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ingest_files WHERE file_path = $1",
                file_path,
            )
            if not row:
                return None
            return self._row_to_record(row)

    async def get_by_id(self, file_id: int) -> IngestFileRecord | None:
        """Get ingest file by ID."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM ingest_files WHERE id = $1",
                file_id,
            )
            if not row:
                return None
            return self._row_to_record(row)

    async def claim_pending_batch(self, limit: int) -> list[IngestFileRecord]:
        """
        Atomically claim a batch of pending files for processing.

        Uses FOR UPDATE SKIP LOCKED for safe parallel worker execution.
        Returns list of claimed file records.
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                UPDATE ingest_files
                SET status = 'processing', updated_at = NOW()
                WHERE id IN (
                    SELECT id FROM ingest_files
                    WHERE status = 'pending'
                    ORDER BY retry_count ASC, created_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING *
                """,
                limit,
            )
            return [self._row_to_record(row) for row in rows]

    async def update_progress(
        self,
        file_id: int,
        last_processed_line: int,
        rows_inserted: int,
        rows_failed: int,
        rows_skipped: int,
    ) -> None:
        """Update file progress (called after each batch commit)."""
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE ingest_files
                SET last_processed_line = $1, rows_inserted = $2,
                    rows_failed = $3, rows_skipped = $4, updated_at = NOW()
                WHERE id = $5
                """,
                last_processed_line,
                rows_inserted,
                rows_failed,
                rows_skipped,
                file_id,
            )

    async def mark_completed(
        self,
        file_id: int,
        rows_total: int,
        rows_inserted: int,
        rows_failed: int,
        rows_skipped: int,
    ) -> None:
        """Mark file as completed."""
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE ingest_files
                SET status = 'completed', rows_total = $1, rows_inserted = $2,
                    rows_failed = $3, rows_skipped = $4, retry_count = 0,
                    error_message = NULL, updated_at = NOW()
                WHERE id = $5
                """,
                rows_total,
                rows_inserted,
                rows_failed,
                rows_skipped,
                file_id,
            )

    async def mark_failed(self, file_id: int, error_message: str, max_retries: int) -> bool:
        """
        Mark file as failed, incrementing retry count.

        Returns True if max retries reached (permanent failure).
        """
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE ingest_files
                SET retry_count = retry_count + 1,
                    error_message = $1,
                    status = CASE
                        WHEN retry_count + 1 >= $2 THEN 'failed'
                        ELSE 'pending'
                    END,
                    updated_at = NOW()
                WHERE id = $3
                RETURNING retry_count, status
                """,
                error_message,
                max_retries,
                file_id,
            )
            return row["status"] == "failed"

    async def reset_to_pending(self, file_ids: list[int]) -> int:
        """Reset files back to pending (for graceful shutdown cleanup)."""
        if not file_ids:
            return 0
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE ingest_files
                SET status = 'pending', updated_at = NOW()
                WHERE id = ANY($1) AND status = 'processing'
                """,
                file_ids,
            )
            return int(result.split()[-1])

    async def reset_stale(self, older_than_minutes: int) -> int:
        """Reset files stuck in 'processing' state for too long."""
        async with self.db.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE ingest_files
                SET status = 'pending', updated_at = NOW()
                WHERE status = 'processing'
                  AND updated_at < NOW() - make_interval(mins => $1)
                """,
                older_than_minutes,
            )
            return int(result.split()[-1])

    async def reset_for_force(self, file_path: str) -> int | None:
        """Reset a completed file to pending for re-ingest (--force flag)."""
        async with self.db.acquire() as conn:
            file_id = await conn.fetchval(
                """
                UPDATE ingest_files
                SET status = 'pending', rows_inserted = 0, rows_failed = 0,
                    rows_skipped = 0, last_processed_line = 0, retry_count = 0,
                    error_message = NULL, updated_at = NOW()
                WHERE file_path = $1
                RETURNING id
                """,
                file_path,
            )
            return file_id

    async def count_by_status(self) -> dict[str, int]:
        """Get counts of files by status."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT status, COUNT(*) as count
                FROM ingest_files
                GROUP BY status
                """
            )
            return {row["status"]: row["count"] for row in rows}

    async def get_stats(self) -> dict:
        """Get overall ingest statistics."""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_files,
                    COUNT(*) FILTER (WHERE status = 'completed') as completed_files,
                    COUNT(*) FILTER (WHERE status = 'failed') as failed_files,
                    COUNT(*) FILTER (WHERE status = 'processing') as processing_files,
                    COUNT(*) FILTER (WHERE status = 'pending') as pending_files,
                    COALESCE(SUM(rows_inserted), 0) as total_inserted,
                    COALESCE(SUM(rows_failed), 0) as total_failed,
                    COALESCE(SUM(rows_skipped), 0) as total_skipped
                FROM ingest_files
                """
            )
            return dict(row)

    def _row_to_record(self, row) -> IngestFileRecord:
        return IngestFileRecord(
            id=row["id"],
            file_path=row["file_path"],
            file_hash=row["file_hash"],
            status=row["status"],
            rows_total=row["rows_total"],
            rows_inserted=row["rows_inserted"],
            rows_failed=row["rows_failed"],
            rows_skipped=row["rows_skipped"],
            last_processed_line=row["last_processed_line"],
            retry_count=row["retry_count"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class PostgresIngestFailedRowRepository(BaseRepository):
    """PostgreSQL implementation of IngestFailedRowRepository."""

    async def create(
        self,
        ingest_file_id: int,
        line_number: int,
        error_message: str,
        raw_content: str | None = None,
    ) -> int:
        """Record a failed row. Returns the row ID."""
        async with self.db.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO ingest_failed_rows
                    (ingest_file_id, line_number, raw_content, error_message)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (ingest_file_id, line_number) DO UPDATE SET
                    error_message = EXCLUDED.error_message,
                    retry_count = ingest_failed_rows.retry_count + 1,
                    updated_at = NOW()
                RETURNING id
                """,
                ingest_file_id,
                line_number,
                raw_content,
                error_message,
            )
            return row_id

    async def get_pending_retry(
        self, ingest_file_id: int | None = None, limit: int = 100
    ) -> list[IngestFailedRowRecord]:
        """Get rows pending retry, optionally filtered by file."""
        async with self.db.acquire() as conn:
            if ingest_file_id:
                rows = await conn.fetch(
                    """
                    SELECT * FROM ingest_failed_rows
                    WHERE status = 'pending_retry' AND ingest_file_id = $1
                    ORDER BY line_number
                    LIMIT $2
                    """,
                    ingest_file_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM ingest_failed_rows
                    WHERE status = 'pending_retry'
                    ORDER BY ingest_file_id, line_number
                    LIMIT $1
                    """,
                    limit,
                )
            return [self._row_to_record(row) for row in rows]

    async def mark_permanent_failure(self, row_id: int) -> None:
        """Mark a row as permanently failed (no more retries)."""
        async with self.db.acquire() as conn:
            await conn.execute(
                """
                UPDATE ingest_failed_rows
                SET status = 'failed_permanent', updated_at = NOW()
                WHERE id = $1
                """,
                row_id,
            )

    async def delete_for_file(self, ingest_file_id: int) -> int:
        """Delete all failed rows for a file (used when re-ingesting with --force)."""
        async with self.db.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM ingest_failed_rows WHERE ingest_file_id = $1",
                ingest_file_id,
            )
            return int(result.split()[-1])

    async def count_by_status(self, ingest_file_id: int | None = None) -> dict[str, int]:
        """Get counts by status, optionally filtered by file."""
        async with self.db.acquire() as conn:
            if ingest_file_id:
                rows = await conn.fetch(
                    """
                    SELECT status, COUNT(*) as count
                    FROM ingest_failed_rows
                    WHERE ingest_file_id = $1
                    GROUP BY status
                    """,
                    ingest_file_id,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT status, COUNT(*) as count
                    FROM ingest_failed_rows
                    GROUP BY status
                    """
                )
            return {row["status"]: row["count"] for row in rows}

    def _row_to_record(self, row) -> IngestFailedRowRecord:
        return IngestFailedRowRecord(
            id=row["id"],
            ingest_file_id=row["ingest_file_id"],
            line_number=row["line_number"],
            raw_content=row["raw_content"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
