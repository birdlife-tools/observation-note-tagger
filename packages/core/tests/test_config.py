"""Tests for configuration loading."""

from ont_core import DatabaseConfig, ExtractorConfig, OllamaConfig


class TestDatabaseConfig:
    def test_defaults(self, monkeypatch):
        # Clear env to test actual default (not .env file)
        monkeypatch.delenv("DATABASE_URL", raising=False)
        config = DatabaseConfig(_env_file=None)
        assert config.database_url == "postgresql://postgres:postgres@localhost:5432/ont"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db:5432/mydb")
        config = DatabaseConfig(_env_file=None)
        assert config.database_url == "postgresql://user:pass@db:5432/mydb"


class TestExtractorConfig:
    def test_defaults(self, monkeypatch):
        # Clear env to test actual defaults
        monkeypatch.delenv("EXTRACTOR_BATCH_SIZE", raising=False)
        monkeypatch.delenv("EXTRACTOR_MAX_RETRIES", raising=False)
        monkeypatch.delenv("EXTRACTOR_CONFIDENCE_THRESHOLD", raising=False)
        monkeypatch.delenv("EXTRACTOR_PARALLEL_WORKERS", raising=False)
        config = ExtractorConfig(_env_file=None)
        assert config.batch_size == 10
        assert config.max_retries == 3
        assert config.confidence_threshold == 0.85
        assert config.parallel_workers == 1

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("EXTRACTOR_BATCH_SIZE", "20")
        monkeypatch.setenv("EXTRACTOR_MAX_RETRIES", "5")
        monkeypatch.setenv("EXTRACTOR_CONFIDENCE_THRESHOLD", "0.9")
        monkeypatch.setenv("EXTRACTOR_PARALLEL_WORKERS", "4")

        config = ExtractorConfig(_env_file=None)
        assert config.batch_size == 20
        assert config.max_retries == 5
        assert config.confidence_threshold == 0.9
        assert config.parallel_workers == 4


class TestOllamaConfig:
    def test_defaults(self):
        config = OllamaConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "qwen2.5:7b"
        assert config.timeout == 120

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://custom:11434")
        monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
        monkeypatch.setenv("OLLAMA_TIMEOUT", "60")

        config = OllamaConfig()
        assert config.base_url == "http://custom:11434"
        assert config.model == "llama3.1:8b"
        assert config.timeout == 60

    def test_explicit_override(self):
        config = OllamaConfig(model="mistral:7b", timeout=30)
        assert config.model == "mistral:7b"
        assert config.timeout == 30
