from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.db.models import ApprovalStatus, EventType, TicketStatus


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
    channel: str | None = None
    metadata: dict[str, Any] | None = None


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


# Approval models


class ApprovalRequestResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    action_type: str
    action_params: dict[str, Any]
    status: ApprovalStatus
    requested_at: datetime
    decided_at: datetime | None
    decided_by: str | None
    decision_reason: str | None


class ApprovalDecisionRequest(BaseModel):
    approved: bool
    decided_by: str = Field(..., min_length=1, max_length=100)
    reason: str | None = Field(None, max_length=1000)


class ApprovalDecisionResponse(BaseModel):
    approval_id: UUID
    ticket_id: UUID
    status: ApprovalStatus
    action_executed: bool
    message: str


# Dashboard stats models


class DashboardStatsResponse(BaseModel):
    total_tickets: int
    pending_tickets: int
    processing_tickets: int
    awaiting_approval_tickets: int
    completed_tickets: int
    failed_tickets: int
    pending_approvals: int


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]
    total: int
    page: int
    page_size: int
