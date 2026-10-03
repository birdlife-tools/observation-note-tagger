"""LLM adapters for extraction."""

from ont_core.adapters.ollama import OllamaAdapter
from ont_core.adapters.protocols import LLMAdapter

__all__ = ["LLMAdapter", "OllamaAdapter"]
