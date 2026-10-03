# Database Migrations

Uses [dbmate](https://github.com/amacneil/dbmate) for schema migrations.

## Setup

1. Start PostgreSQL:
   ```bash
   docker compose up -d postgres
   ```

2. Copy env file:
   ```bash
   cp .env.example .env
   ```

3. Run migrations:
   ```bash
   # Via Docker (no install needed)
   docker run --rm --network=host -v "$(pwd)/db:/db" ghcr.io/amacneil/dbmate \
     -u "postgresql://ont:ont_dev@localhost:5432/ont" up

   # Or install locally: brew install dbmate
   dbmate up
   ```

## Commands

```bash
dbmate status      # Show migration status
dbmate up          # Apply pending migrations
dbmate down        # Rollback last migration
dbmate new <name>  # Create new migration file
```

## Schema

### Core Tables

| Table | Purpose |
|-------|---------|
| `observations` | Raw eBird observation notes (species, date, location, note text) |
| `extractions` | Structured data extracted by LLM (behaviors, breeding evidence, etc.) |

### Pipeline Tables

| Table | Purpose |
|-------|---------|
| `ingest_files` | File-level progress tracking and checkpointing |
| `ingest_failed_rows` | Row-level error tracking for retry |

### Provenance

| Table | Purpose |
|-------|---------|
| `lineage_events` | Full audit trail — traces any extraction back to source file + line |

Lineage events track: `ingested` → `extracted` → `reviewed` with model version, prompt, response, and latency.
