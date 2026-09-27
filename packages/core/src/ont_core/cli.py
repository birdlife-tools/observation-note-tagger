"""CLI for running the extraction engine."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys

from ont_core.adapters.ollama import OllamaAdapter
from ont_core.config import DatabaseConfig, ExtractorConfig, OllamaConfig
from ont_core.extractor import Extractor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_extract(args: argparse.Namespace) -> int:
    """Run the extraction engine."""
    # Load configs from environment
    db_config = DatabaseConfig()
    extractor_config = ExtractorConfig()
    ollama_config = OllamaConfig()

    # Override config from CLI args
    if args.batch or args.workers:
        extractor_config = ExtractorConfig(
            batch_size=args.batch or extractor_config.batch_size,
            max_retries=extractor_config.max_retries,
            confidence_threshold=extractor_config.confidence_threshold,
            parallel_workers=args.workers or extractor_config.parallel_workers,
        )

    logger.info(f"Database: {db_config.database_url}")
    logger.info(f"Ollama: {ollama_config.base_url} model={ollama_config.model}")
    logger.info(
        f"Extractor: batch={extractor_config.batch_size}, "
        f"workers={extractor_config.parallel_workers}, "
        f"max_retries={extractor_config.max_retries}"
    )

    # Create adapter and extractor
    adapter = OllamaAdapter(ollama_config)
    extractor = await Extractor.create(adapter, db_config, extractor_config)

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
    parser = argparse.ArgumentParser(description="Observation Note Tagger - Extraction Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    if args.command == "extract":
        return asyncio.run(run_extract(args))

    return 0


if __name__ == "__main__":
    sys.exit(main())
