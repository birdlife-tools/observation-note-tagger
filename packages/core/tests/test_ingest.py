"""Tests for ingest engine."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from ont_core.config import IngestConfig
from ont_core.ingest import IngestEngine, IngestStats


class TestIngestConfig:
    """Tests for IngestConfig defaults."""

    def test_default_values(self):
        config = IngestConfig()
        assert config.batch_size == 1000
        assert config.max_retries == 3
        assert config.checkpoint_interval == 5000
        assert config.stale_timeout_minutes == 30


class TestIngestStats:
    """Tests for IngestStats."""

    def test_default_values(self):
        stats = IngestStats()
        assert stats.files_found == 0
        assert stats.files_processed == 0
        assert stats.files_skipped == 0
        assert stats.files_failed == 0
        assert stats.rows_inserted == 0
        assert stats.rows_failed == 0
        assert stats.rows_skipped == 0
        assert stats.elapsed_seconds == 0.0


class TestIngestEngine:
    """Tests for IngestEngine helper methods."""

    @pytest.fixture
    def mock_engine(self):
        """Create engine with mocked dependencies."""
        parser = MagicMock()
        parser.file_pattern = "ebd_*.txt"
        parser.validate_file.return_value = True  # All files valid by default

        engine = IngestEngine(
            parser=parser,
            observation_repo=AsyncMock(),
            file_repo=AsyncMock(),
            failed_row_repo=AsyncMock(),
            lineage_repo=AsyncMock(),
            config=IngestConfig(),
        )
        return engine

    def test_discover_files_finds_matching(self, mock_engine):
        """Discovers files matching parser's pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create matching files
            (tmppath / "ebd_US_202401.txt").touch()
            (tmppath / "ebd_SE_202402.txt").touch()

            # Create non-matching files
            (tmppath / "other.txt").touch()
            (tmppath / "ebd_backup.csv").touch()

            files = mock_engine._discover_files(tmppath)

            assert len(files) == 2
            names = {f.name for f in files}
            assert names == {"ebd_US_202401.txt", "ebd_SE_202402.txt"}

    def test_discover_files_empty_dir(self, mock_engine):
        """Returns empty list for directory with no matching files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = mock_engine._discover_files(Path(tmpdir))
            assert files == []

    def test_discover_files_recursive(self, mock_engine):
        """Discovers files in subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create nested structure
            subdir1 = tmppath / "region1"
            subdir2 = tmppath / "region2" / "2024"
            subdir1.mkdir()
            subdir2.mkdir(parents=True)

            # Files at various levels
            (tmppath / "ebd_root.txt").touch()
            (subdir1 / "ebd_region1.txt").touch()
            (subdir2 / "ebd_region2_deep.txt").touch()

            files = mock_engine._discover_files(tmppath)

            assert len(files) == 3
            names = {f.name for f in files}
            assert names == {"ebd_root.txt", "ebd_region1.txt", "ebd_region2_deep.txt"}

    def test_discover_files_skips_invalid(self, mock_engine):
        """Skips files that fail validation."""

        # Make validate_file return False for specific files
        def validate_side_effect(path):
            return "sampling" not in path.name

        mock_engine.parser.validate_file.side_effect = validate_side_effect

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "ebd_US_202401.txt").touch()  # Valid
            (tmppath / "ebd_sampling_US_202401.txt").touch()  # Invalid (sampling)

            files = mock_engine._discover_files(tmppath)

            assert len(files) == 1
            assert files[0].name == "ebd_US_202401.txt"

    def test_discover_files_sorted(self, mock_engine):
        """Returns files in sorted order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            (tmppath / "ebd_ZZ_last.txt").touch()
            (tmppath / "ebd_AA_first.txt").touch()
            (tmppath / "ebd_MM_middle.txt").touch()

            files = mock_engine._discover_files(tmppath)

            assert [f.name for f in files] == [
                "ebd_AA_first.txt",
                "ebd_MM_middle.txt",
                "ebd_ZZ_last.txt",
            ]

    def test_compute_hash(self, mock_engine):
        """Computes consistent SHA256 hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content for hashing")
            path = Path(f.name)

        hash1 = mock_engine._compute_hash(path)
        hash2 = mock_engine._compute_hash(path)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex digest
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_compute_hash_different_content(self, mock_engine):
        """Different content produces different hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f1:
            f1.write("content A")
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f2:
            f2.write("content B")
            path2 = Path(f2.name)

        assert mock_engine._compute_hash(path1) != mock_engine._compute_hash(path2)

    def test_update_stats(self, mock_engine):
        """Aggregates stats correctly."""
        total = IngestStats(
            files_processed=5,
            rows_inserted=1000,
            rows_failed=10,
        )

        delta = IngestStats(
            files_processed=2,
            files_failed=1,
            rows_inserted=500,
            rows_failed=5,
            rows_skipped=100,
        )

        mock_engine._update_stats(total, delta)

        assert total.files_processed == 7
        assert total.files_failed == 1
        assert total.rows_inserted == 1500
        assert total.rows_failed == 15
        assert total.rows_skipped == 100
