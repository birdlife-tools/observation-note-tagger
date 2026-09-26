# ont-core

Core extraction engine and LLM adapters for observation-note-tagger.

## Installation

```bash
pip install ont-core
```

## Configuration

Copy `.env-sample` to `.env` and configure:

```bash
# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=120
```

## Usage

```python
from ont_core.adapters import OllamaAdapter

# Uses OLLAMA_* env vars automatically
adapter = OllamaAdapter()

# Or override with custom config
from ont_core import OllamaConfig

adapter = OllamaAdapter(OllamaConfig(model="llama3.1:8b"))

result = await adapter.extract(
    note="Singing male on territory, 2 fledglings nearby", species="European Robin"
)
print(result.behaviors)
print(result.breeding_evidence)
```

## License

MIT
