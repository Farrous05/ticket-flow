from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.db.models import EventType, TicketStatus


class CreateTicketRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=10000)
    customer_id: str = Field(..., min_length=1, max_length=100)


class CreateTicketResponse(BaseModel):
    ticket_id: UUID
    status: TicketStatus


class TicketResponse(BaseModel):
    id: UUID
    customer_id: str
    subject: str
    body: str
    status: TicketStatus
    result: dict[str, Any] | None
    attempt_count: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class TicketEventResponse(BaseModel):
    id: UUID
    event_type: EventType
    step_name: str | None
    payload: dict[str, Any] | None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str
    queue: str
