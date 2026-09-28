"""CLI for running the extraction and ingest engines."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path

from ont_core.config import AppConfig, DatabaseConfig, ExtractorConfig, IngestConfig
from ont_core.factory import create_extractor, create_ingest_engine, create_llm_adapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_ingest(args: argparse.Namespace) -> int:
    """Run the ingest engine to load EBD files."""
    # Load configs from environment
    app_config = AppConfig()
    db_config = DatabaseConfig()
    ingest_config = IngestConfig()

    # Override config from CLI args
    if args.batch:
        ingest_config = IngestConfig(
            batch_size=args.batch,
            max_retries=ingest_config.max_retries,
            checkpoint_interval=ingest_config.checkpoint_interval,
            stale_timeout_minutes=ingest_config.stale_timeout_minutes,
        )

    directory = Path(args.dir).resolve()
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return 1

    logger.info(f"Ingest directory: {directory}")
    logger.info(f"Backend: repo={app_config.repo_backend}, parser={app_config.parser}")
    logger.info(
        f"Config: batch={ingest_config.batch_size}, workers={args.workers}, "
        f"force={args.force}, dry_run={args.dry_run}"
    )

    # Create engine via factory
    engine = await create_ingest_engine(db_config, ingest_config, app_config)

    try:
        stats = await engine.run(
            directory=directory,
            workers=args.workers,
            force=args.force,
            dry_run=args.dry_run,
        )

        # Print summary
        logger.info("=" * 60)
        logger.info("INGEST COMPLETE")
        logger.info(f"  Files found:     {stats.files_found}")
        logger.info(f"  Files processed: {stats.files_processed}")
        logger.info(f"  Files skipped:   {stats.files_skipped}")
        logger.info(f"  Files failed:    {stats.files_failed}")
        logger.info(f"  Rows inserted:   {stats.rows_inserted}")
        logger.info(f"  Rows failed:     {stats.rows_failed}")
        logger.info(f"  Rows skipped:    {stats.rows_skipped} (no notes)")
        logger.info(f"  Elapsed:         {stats.elapsed_seconds:.1f}s")
        if stats.rows_inserted > 0 and stats.elapsed_seconds > 0:
            rate = stats.rows_inserted / stats.elapsed_seconds
            logger.info(f"  Rate:            {rate:.0f} rows/sec")
        logger.info("=" * 60)

        return 0 if stats.files_failed == 0 else 1

    except Exception as e:
        logger.exception(f"Ingest failed: {e}")
        return 1
    finally:
        await engine.cleanup()
        if hasattr(engine, "_db_pool") and engine._db_pool:
            await engine._db_pool.close()


async def run_extract(args: argparse.Namespace) -> int:
    """Run the extraction engine."""
    # Load configs from environment
    app_config = AppConfig()
    db_config = DatabaseConfig()
    extractor_config = ExtractorConfig()

    # Override config from CLI args
    if args.batch or args.workers:
        extractor_config = ExtractorConfig(
            batch_size=args.batch or extractor_config.batch_size,
            max_retries=extractor_config.max_retries,
            confidence_threshold=extractor_config.confidence_threshold,
            parallel_workers=args.workers or extractor_config.parallel_workers,
        )

    logger.info(f"Backend: repo={app_config.repo_backend}, llm={app_config.llm_adapter}")
    logger.info(f"Database: {db_config.database_url}")
    logger.info(
        f"Extractor: batch={extractor_config.batch_size}, "
        f"workers={extractor_config.parallel_workers}, "
        f"max_retries={extractor_config.max_retries}"
    )

    # Create adapter and extractor via config-driven factory
    adapter = create_llm_adapter(app_config)
    extractor = await create_extractor(adapter, db_config, extractor_config, app_config)

    # Setup graceful shutdown
    def handle_signal(signum, frame):
        logger.info("Shutdown signal received, finishing current batch...")
        extractor.request_stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        workers = args.workers or extractor_config.parallel_workers

        if workers > 1 or args.all:
            # Parallel mode: run until all pending processed
            stats = await extractor.run_workers(num_workers=workers)
            logger.info(
                f"Completed: {stats.total_processed} processed "
                f"({stats.succeeded} ok, {stats.failed} failed) "
                f"in {stats.duration_seconds:.1f}s"
            )
        else:
            # Single batch mode
            outcomes = await extractor.run_batch(args.batch)
            succeeded = sum(1 for o in outcomes if o.success)
            logger.info(f"Completed: {succeeded}/{len(outcomes)} succeeded")
        return 0
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return 1
    finally:
        await extractor.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Observation Note Tagger CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Load EBD files into database")
    ingest_parser.add_argument(
        "--dir", "-d", type=str, required=True, help="Directory containing EBD files"
    )
    ingest_parser.add_argument(
        "--workers", "-w", type=int, default=1, help="Number of parallel workers (default: 1)"
    )
    ingest_parser.add_argument(
        "--batch", "-b", type=int, help="Batch size for INSERT (default: 1000)"
    )
    ingest_parser.add_argument(
        "--force", "-f", action="store_true", help="Re-ingest already completed files"
    )
    ingest_parser.add_argument(
        "--dry-run", action="store_true", help="Validate files without inserting"
    )

    # extract command
    extract_parser = subparsers.add_parser("extract", help="Run extraction on pending observations")
    extract_parser.add_argument(
        "--batch", "-b", type=int, help="Batch size per worker (default: 10)"
    )
    extract_parser.add_argument(
        "--workers", "-w", type=int, help="Number of parallel workers (default: 1)"
    )
    extract_parser.add_argument(
        "--all", "-a", action="store_true", help="Process all pending (runs until queue empty)"
    )

    args = parser.parse_args()

    if args.command == "ingest":
        return asyncio.run(run_ingest(args))
    elif args.command == "extract":
        return asyncio.run(run_extract(args))

    return 0


if __name__ == "__main__":
    sys.exit(main())
