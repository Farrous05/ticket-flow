"""Request tracing utilities."""

import uuid
from contextvars import ContextVar
from typing import Optional

import structlog

# Context variable to store request ID across async boundaries
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_ctx.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    request_id_ctx.set(request_id)
    # Also bind to structlog context
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_id() -> None:
    """Clear the request ID from context."""
    request_id_ctx.set(None)
    structlog.contextvars.unbind_contextvars("request_id")
