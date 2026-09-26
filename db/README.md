# Database Migrations

Uses [dbmate](https://github.com/amacneil/dbmate) for schema migrations.

## Setup

1. Start PostgreSQL:
   ```bash
   docker compose up -d postgres
   ```

2. Copy env file (or use defaults):
   ```bash
   cp .env-sample .env
   ```

3. Run migrations:
   ```bash
   # Via Docker (no install needed)
   docker run --rm --network=host -v "$(pwd)/db:/db" ghcr.io/amacneil/dbmate \
     -u "postgres://ont:ont_dev@localhost:5432/ont?sslmode=disable" up

   # Or install locally: brew install dbmate
   dbmate -u "$DATABASE_URL" up
   ```

## Commands

```bash
dbmate status      # Show migration status
dbmate up          # Apply pending migrations
dbmate down        # Rollback last migration
dbmate new <name>  # Create new migration file
```

## Schema

- `observations` — Raw eBird observation notes
- `extractions` — Structured data extracted by LLM
- `extraction_audit` — Full audit trail (prompt, response, latency)
