# birdlife-ont-core

Core extraction engine, protocols, and adapters for observation-note-tagger.

## Installation

```bash
pip install birdlife-ont-core
```

## Protocols (Extension Points)

Build custom adapters by implementing these protocols:

### LLMAdapter

```python
from ont_core.adapters import LLMAdapter
from ont_core.schemas import ExtractionResult

class MyLLMAdapter:
    """Implements LLMAdapter protocol."""
    
    @property
    def name(self) -> str:
        return "my-llm"
    
    @property
    def model_version(self) -> str:
        return "v1.0"
    
    async def extract(self, note: str, species: str) -> ExtractionResult:
        # Your extraction logic
        ...
```

### Parser

```python
from ont_core.parsers import Parser, ParsedObservation
from pathlib import Path
from collections.abc import Iterator

class MyParser:
    """Implements Parser protocol."""
    
    @property
    def name(self) -> str:
        return "my-format"
    
    @property
    def file_pattern(self) -> str:
        return "*.myformat"
    
    def validate_file(self, path: Path) -> bool:
        ...
    
    def parse(self, path: Path) -> Iterator[ParsedObservation]:
        ...
    
    def count_rows(self, path: Path) -> int:
        ...
```

### Validator

```python
from ont_core.validators import Validator, ValidationResult
from ont_core.schemas import ExtractionResult

class MyValidator:
    """Implements Validator protocol."""
    
    def validate(self, result: ExtractionResult, note: str) -> ValidationResult:
        # Your validation logic
        ...
```

## Built-in Adapters

### OllamaAdapter (local LLM)

```python
from ont_core.adapters import OllamaAdapter
from ont_core.config import OllamaConfig

adapter = OllamaAdapter()  # Uses OLLAMA_* env vars

# Or with explicit config
adapter = OllamaAdapter(OllamaConfig(
    base_url="http://localhost:11434",
    model="qwen2.5:7b"
))

result = await adapter.extract(
    note="Singing male on territory, 2 fledglings nearby",
    species="European Robin"
)
```

## Factory Pattern

Use the factory for config-driven wiring:

```python
from ont_core.factory import create_llm_adapter, create_extractor

# Adapter selection via ONT_LLM_ADAPTER env var
adapter = create_llm_adapter()

# Full extractor with repositories
extractor = await create_extractor()
```

## Environment Variables

```bash
# Backend selection
ONT_LLM_ADAPTER=ollama     # ollama | claude | openai
ONT_VALIDATOR=grounding    # grounding | composite | none
ONT_REPO_BACKEND=postgres  # postgres | memory

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

## License

MIT
