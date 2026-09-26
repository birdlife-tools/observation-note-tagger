# Observation Note Tagger

Extract structured data from bird observation notes using LLMs.

## Problem

eBird contains 1.5+ billion bird observations. Many include free-text notes like:

> "Singing male on territory, tall oak at forest edge, 2 juveniles nearby"

This describes behavior, breeding evidence, habitat, and life stages — but it's buried in unstructured text. Researchers wanting to answer "show me all territorial behavior for Cuckoo in April" must manually read thousands of notes.

## Solution

A configurable pipeline that extracts structured data from observation notes:

```
INPUT:  "Singing from dead snag at forest edge. 2 fledglings begging nearby."

OUTPUT:
{
  "behaviors": [{"type": "singing", "context": "territorial"}],
  "breeding_evidence": {"code": "FL", "description": "fledglings begging"},
  "habitat_features": ["dead_snag", "forest_edge"],
  "life_stages": ["adult", "fledgling"]
}
```

### Key Features

- **Swappable LLM adapters** — Ollama (local, free), Claude, OpenAI
- **Human-in-loop review** — low-confidence extractions routed for review
- **Full audit trail** — every extraction logged with model version, prompt, response
- **Pluggable validators** — schema validation, taxonomy checks, consistency rules
- **Production-ready** — async pipeline, retry logic, job state management

## Technical Stack

- **Backend:** Python + FastAPI + async pipeline
- **Database:** PostgreSQL (observations, extractions, audit)
- **LLM:** Ollama (local default) + Claude/OpenAI adapters
- **API:** REST (admin/pipeline) + GraphQL (data queries)
- **Frontend:** React + TypeScript (admin UI, review interface)
- **Deployment:** Docker Compose (local/demo), systemd (production)

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Ingest    │───▶│   Extract   │───▶│   Review    │
│  (FastAPI)  │    │  (LLM/NLP)  │    │   (React)   │
└─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  PostgreSQL │    │   Adapters  │    │   Quality   │
│  (raw data) │    │ Ollama/Claude│    │   Metrics   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Status

🔧 In Progress

## Community

[![Matrix](https://img.shields.io/badge/Matrix-Chat-black?logo=matrix)](https://matrix.to/#/#birdlife-tools:matrix.org)

## License

MIT — see [LICENSE](LICENSE)
