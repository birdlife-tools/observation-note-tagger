"""Configuration via environment variables (12-factor)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class OllamaConfig(BaseSettings):
    """Ollama adapter configuration."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_")

    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:7b"
    timeout: int = 120


class ClaudeConfig(BaseSettings):
    """Claude adapter configuration (for future use)."""

    model_config = SettingsConfigDict(env_prefix="")

    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_timeout: int = 120


class OpenAIConfig(BaseSettings):
    """OpenAI adapter configuration (for future use)."""

    model_config = SettingsConfigDict(env_prefix="")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_timeout: int = 120
