"""Configuration via environment variables (12-factor)."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application-wide configuration for swappable backends."""

    model_config = SettingsConfigDict(env_prefix="ONT_", env_file=".env", extra="ignore")

    # Repository backend: "postgres" or "memory" (for testing)
    repo_backend: Literal["postgres", "memory"] = "postgres"

    # LLM adapter: "ollama", "claude", or "openai"
    llm_adapter: Literal["ollama", "claude", "openai"] = "ollama"


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@localhost:5432/ont"


class ExtractorConfig(BaseSettings):
    """Extractor engine configuration."""

    model_config = SettingsConfigDict(env_prefix="EXTRACTOR_", env_file=".env", extra="ignore")

    batch_size: int = 10
    max_retries: int = 3
    confidence_threshold: float = 0.85
    parallel_workers: int = 1


class OllamaConfig(BaseSettings):
    """Ollama adapter configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_", env_file=".env", extra="ignore")

    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    timeout: int = 120


class ClaudeConfig(BaseSettings):
    """Claude adapter configuration (for future use)."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_timeout: int = 120


class OpenAIConfig(BaseSettings):
    """OpenAI adapter configuration (for future use)."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_timeout: int = 120
