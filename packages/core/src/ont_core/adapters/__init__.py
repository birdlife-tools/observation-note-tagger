"""LLM adapters for extraction."""

from ont_core.adapters.base import LLMAdapter
from ont_core.adapters.ollama import OllamaAdapter

__all__ = ["LLMAdapter", "OllamaAdapter"]
