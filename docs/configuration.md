# Configuration Guide

This document describes all environment variables used by Ticket Flow.

## Required Variables

These variables must be set for the system to function:

| Variable | Description | Example |
|----------|-------------|---------|
| `SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Supabase service role key (not anon key) | `eyJhbGciOiJIUzI1...` |
| `OPENAI_API_KEY` | OpenAI API key for LLM calls | `sk-...` |

> **Important**: Use the `service_role` key from Supabase, not the `anon` key. The service role key bypasses Row Level Security (RLS) policies.

## Optional Variables

These variables have sensible defaults:

### RabbitMQ

| Variable | Description | Default |
|----------|-------------|---------|
| `RABBITMQ_URL` | RabbitMQ connection URL | `amqp://guest:guest@localhost:5672/` |
| `QUEUE_NAME` | Name of the processing queue | `ticket_processing` |
| `DLX_NAME` | Dead letter exchange name | `ticket_processing_dlx` |
| `PREFETCH_COUNT` | Messages per worker before ack | `1` |

### Application

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKER_ID` | Unique identifier for this worker | `worker-1` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) | `INFO` |
| `MAX_RETRIES` | Max processing attempts before DLX | `3` |

### Worker

| Variable | Description | Default |
|----------|-------------|---------|
| `HEARTBEAT_INTERVAL_SECONDS` | How often worker sends heartbeat | `30` |
| `STALE_PROCESSING_THRESHOLD_SECONDS` | When to consider processing stale | `300` (5 min) |

### LLM

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_TIMEOUT_SECONDS` | Timeout for LLM API calls | `60` |
| `LLM_MAX_RETRIES` | Retries for failed LLM calls | `2` |

## Example .env File

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=sk-your-openai-key

# RabbitMQ (optional if using default)
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Application (optional)
WORKER_ID=worker-1
LOG_LEVEL=INFO
MAX_RETRIES=3

# Worker (optional)
HEARTBEAT_INTERVAL_SECONDS=30
STALE_PROCESSING_THRESHOLD_SECONDS=300

# LLM (optional)
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
```

## Docker Compose Environment

When running with Docker Compose, environment variables can be set in:

1. **`.env` file** (recommended for local development)
2. **`docker-compose.yml`** under `environment:` section
3. **Shell environment** before running `docker compose up`

### Docker Compose Example

```yaml
services:
  api:
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
```

## Scaling Configuration

When running multiple workers:

1. **Set unique `WORKER_ID`** for each worker instance
2. **Keep `PREFETCH_COUNT=1`** for fair distribution
3. **Adjust `HEARTBEAT_INTERVAL_SECONDS`** based on expected processing time

```bash
# Worker 1
WORKER_ID=worker-1

# Worker 2
WORKER_ID=worker-2

# Worker 3
WORKER_ID=worker-3
```

Or with Docker Compose scaling:
```bash
docker compose up --scale worker=3
```
(Worker IDs are auto-generated based on hostname)

## Security Notes

1. **Never commit `.env` files** to version control
2. **Use `service_role` key** for Supabase (bypasses RLS)
3. **Rotate keys regularly** in production
4. **Use secrets management** (Vault, AWS Secrets Manager) in production
