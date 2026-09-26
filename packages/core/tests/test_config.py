"""Tests for configuration loading."""

from ont_core import OllamaConfig


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
