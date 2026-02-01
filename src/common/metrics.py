"""Prometheus metrics for observability."""

from prometheus_client import Counter, Gauge, Histogram

# API metrics
TICKETS_CREATED = Counter(
    "tickets_created_total",
    "Total number of tickets created",
    ["status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Worker metrics
TICKETS_PROCESSED = Counter(
    "tickets_processed_total",
    "Total number of tickets processed",
    ["status"],  # completed, failed, retried
)

WORKFLOW_STEP_DURATION = Histogram(
    "workflow_step_duration_seconds",
    "Duration of each workflow step",
    ["step"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

PROCESSING_DURATION = Histogram(
    "ticket_processing_duration_seconds",
    "Total ticket processing duration",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "queue_depth",
    "Current number of messages in the queue",
)

ACTIVE_WORKERS = Gauge(
    "active_workers",
    "Number of active worker instances",
)

# Database metrics
DB_OPERATIONS = Counter(
    "db_operations_total",
    "Total database operations",
    ["operation", "table"],
)

DB_OPERATION_DURATION = Histogram(
    "db_operation_duration_seconds",
    "Database operation duration",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)
