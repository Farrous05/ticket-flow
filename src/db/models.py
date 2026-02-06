from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED_PERMANENT = "failed_permanent"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Ticket(BaseModel):
    id: UUID
    customer_id: str
    subject: str
    body: str
    status: TicketStatus = TicketStatus.PENDING
    result: dict[str, Any] | None = None
    worker_id: str | None = None
    attempt_count: int = 0
    version: int = 1
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_heartbeat: datetime | None = None


class TicketCreate(BaseModel):
    id: UUID
    customer_id: str
    subject: str
    body: str


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    result: dict[str, Any] | None = None
    worker_id: str | None = None
    attempt_count: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_heartbeat: datetime | None = None


class EventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGE = "status_change"
    STEP_COMPLETE = "step_complete"
    ERROR = "error"
    RETRY = "retry"


class TicketEvent(BaseModel):
    id: UUID
    ticket_id: UUID
    event_type: EventType
    step_name: str | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime


class TicketEventCreate(BaseModel):
    ticket_id: UUID
    event_type: EventType
    step_name: str | None = None
    payload: dict[str, Any] | None = None


class WorkflowCheckpoint(BaseModel):
    ticket_id: UUID
    state: dict[str, Any]
    current_step: str
    updated_at: datetime


class WorkflowCheckpointUpsert(BaseModel):
    ticket_id: UUID
    state: dict[str, Any]
    current_step: str


class ApprovalRequest(BaseModel):
    id: UUID
    ticket_id: UUID
    action_type: str
    action_params: dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_reason: str | None = None


class ApprovalRequestCreate(BaseModel):
    ticket_id: UUID
    action_type: str
    action_params: dict[str, Any]


class ApprovalDecision(BaseModel):
    approved: bool
    decided_by: str
    reason: str | None = None
