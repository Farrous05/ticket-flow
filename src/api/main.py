import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.api.routes import router
from src.common.logging import get_logger, setup_logging
from src.common.metrics import REQUEST_DURATION
from src.common.tracing import clear_request_id, generate_request_id, set_request_id

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("api_starting")
    yield
    logger.info("api_shutting_down")


app = FastAPI(
    title="Ticket Flow API",
    description="Customer support ticket processing system",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    """Add request ID tracing to all requests."""
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID") or generate_request_id()
    set_request_id(request_id)

    # Track timing
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration = time.perf_counter() - start_time

        # Record metrics
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).observe(duration)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_request_id()


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
