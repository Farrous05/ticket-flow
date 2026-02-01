# Ticket Flow

Production-grade agentic AI workflow system for processing customer support tickets.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  RabbitMQ   │────▶│   Worker    │────▶│  Supabase   │
│   Ingestion │     │   Queue     │     │  (LangGraph)│     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Flow:**
1. API receives ticket → validates → writes to DB → publishes to queue
2. Worker consumes message → executes LangGraph workflow → updates DB
3. All state changes persisted with timestamps for auditability

## Features

- **Async Processing**: Tickets processed via message queue for reliability
- **Idempotency**: Deterministic ticket IDs prevent duplicate processing
- **Resumability**: Workflow checkpoints allow recovery from crashes
- **Observability**: Structured logging, Prometheus metrics, event trail
- **Optimistic Locking**: Version column prevents race conditions

## Tech Stack

- **API**: FastAPI
- **Queue**: RabbitMQ
- **Database**: Supabase (PostgreSQL)
- **Workflow**: LangGraph
- **Containerization**: Docker

## Project Structure

```
src/
├── api/           # FastAPI ingestion service
├── worker/        # Queue consumer and processor
├── workflow/      # LangGraph workflow definition
├── db/            # Supabase client and repositories
└── common/        # Shared utilities and config
tests/             # Test suite
docker/            # Docker configurations
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- RabbitMQ
- Supabase account (or local instance)
- OpenAI API key (for LLM calls)

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Farrous05/ticket-flow.git
cd ticket-flow
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -e ".[dev]"
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

Required variables:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
OPENAI_API_KEY=your_openai_key
```

### 5. Start infrastructure (Docker)

```bash
docker-compose up -d rabbitmq
```

### 6. Run database migrations

```bash
# Apply migrations to Supabase
psql $DATABASE_URL -f migrations/001_initial.sql
```

### 7. Start the services

**API Service:**
```bash
uvicorn src.api.main:app --reload --port 8000
```

**Worker Service:**
```bash
python -m src.worker.main
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tickets` | Create a new ticket |
| GET | `/tickets/{id}` | Get ticket status and result |
| GET | `/tickets/{id}/events` | Get processing events |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Create Ticket

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Cannot access my account",
    "body": "I have been trying to login but keep getting an error...",
    "customer_id": "cust_12345"
  }'
```

Response:
```json
{
  "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending"
}
```

### Check Status

```bash
curl http://localhost:8000/tickets/550e8400-e29b-41d4-a716-446655440000
```

## Workflow Steps

The LangGraph workflow processes tickets through these sequential steps:

1. **Classify** - Categorize ticket (billing, technical, general)
2. **Extract** - Extract key entities (order_id, product, issue_type)
3. **Research** - Query knowledge base for relevant information
4. **Draft** - Generate response draft
5. **Review** - Self-review for quality and policy compliance
6. **Finalize** - Produce final response

## Database Schema

### tickets
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| customer_id | text | Customer identifier |
| subject | text | Ticket subject |
| body | text | Ticket body |
| status | enum | pending, processing, completed, failed_permanent |
| result | jsonb | Final workflow output |
| version | int | Optimistic lock version |

### ticket_events
| Column | Type | Description |
|--------|------|-------------|
| id | uuid | Primary key |
| ticket_id | uuid | Foreign key to tickets |
| event_type | text | status_change, step_complete, error, retry |
| payload | jsonb | Event-specific data |

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_api.py
```

## Docker Deployment

```bash
# Build and run entire stack
docker-compose up --build

# Scale workers
docker-compose up --scale worker=3
```

## Workflow Visualization

Generate a visual diagram of the LangGraph workflow:

```bash
python -m src.workflow.visualize workflow_graph.png
```

This outputs:
- ASCII diagram to console
- Mermaid diagram syntax
- PNG image (if graphviz installed)

## Monitoring

- **Metrics**: Prometheus metrics available at `/metrics`
- **Logs**: Structured JSON logs to stdout
- **Events**: Query `/tickets/{id}/events` for processing trail
- **Tracing**: X-Request-ID header propagated through all components

### Available Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `tickets_created_total` | Counter | Total tickets created |
| `tickets_processed_total` | Counter | Total tickets processed by status |
| `http_request_duration_seconds` | Histogram | API request latency |
| `workflow_step_duration_seconds` | Histogram | Per-step workflow timing |
| `ticket_processing_duration_seconds` | Histogram | Total processing time |

## Failure Handling

| Scenario | Handling |
|----------|----------|
| Worker crash | Message redelivered, processing resumes from checkpoint |
| LLM timeout | Retry with exponential backoff (3 attempts) |
| Duplicate submission | Idempotent - returns existing ticket |
| DB connection lost | Retry with backoff, fail after persistent errors |

## License

MIT
