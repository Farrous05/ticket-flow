from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from supabase import Client

from src.common.logging import get_logger
from src.db.client import get_supabase_client
from src.db.models import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalRequestCreate,
    ApprovalStatus,
    EventType,
    Ticket,
    TicketCreate,
    TicketEvent,
    TicketEventCreate,
    TicketStatus,
    TicketUpdate,
    WorkflowCheckpoint,
    WorkflowCheckpointUpsert,
)

logger = get_logger(__name__)


class OptimisticLockError(Exception):
    """Raised when optimistic lock version mismatch occurs."""

    pass


class TicketNotFoundError(Exception):
    """Raised when ticket is not found."""

    pass


class TicketRepository:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create(self, ticket: TicketCreate) -> Ticket:
        data = {
            "id": str(ticket.id),
            "customer_id": ticket.customer_id,
            "subject": ticket.subject,
            "body": ticket.body,
            "status": TicketStatus.PENDING.value,
        }
        result = self.client.table("tickets").insert(data).execute()
        return Ticket(**result.data[0])

    def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        result = (
            self.client.table("tickets")
            .select("*")
            .eq("id", str(ticket_id))
            .execute()
        )
        if not result.data:
            return None
        return Ticket(**result.data[0])

    def exists(self, ticket_id: UUID) -> bool:
        result = (
            self.client.table("tickets")
            .select("id")
            .eq("id", str(ticket_id))
            .execute()
        )
        return len(result.data) > 0

    def update(
        self, ticket_id: UUID, update: TicketUpdate, expected_version: int | None = None
    ) -> Ticket:
        data: dict[str, Any] = {}
        if update.status is not None:
            data["status"] = update.status.value
        if update.result is not None:
            data["result"] = update.result
        if update.worker_id is not None:
            data["worker_id"] = update.worker_id
        if update.attempt_count is not None:
            data["attempt_count"] = update.attempt_count
        if update.started_at is not None:
            data["started_at"] = update.started_at.isoformat()
        if update.completed_at is not None:
            data["completed_at"] = update.completed_at.isoformat()
        if update.last_heartbeat is not None:
            data["last_heartbeat"] = update.last_heartbeat.isoformat()

        if not data:
            ticket = self.get_by_id(ticket_id)
            if ticket is None:
                raise TicketNotFoundError(f"Ticket {ticket_id} not found")
            return ticket

        query = self.client.table("tickets").update(data).eq("id", str(ticket_id))

        if expected_version is not None:
            query = query.eq("version", expected_version)

        result = query.execute()

        if not result.data:
            if expected_version is not None:
                raise OptimisticLockError(
                    f"Version mismatch for ticket {ticket_id}. Expected {expected_version}"
                )
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        return Ticket(**result.data[0])

    def update_heartbeat(self, ticket_id: UUID, worker_id: str) -> None:
        now = datetime.now(timezone.utc)
        self.client.table("tickets").update(
            {"last_heartbeat": now.isoformat(), "worker_id": worker_id}
        ).eq("id", str(ticket_id)).execute()

    def acquire_for_processing(
        self, ticket_id: UUID, worker_id: str, expected_version: int
    ) -> Ticket:
        now = datetime.now(timezone.utc)
        update = TicketUpdate(
            status=TicketStatus.PROCESSING,
            worker_id=worker_id,
            started_at=now,
            last_heartbeat=now,
        )
        return self.update(ticket_id, update, expected_version=expected_version)

    def mark_completed(
        self, ticket_id: UUID, result: dict[str, Any], expected_version: int
    ) -> Ticket:
        now = datetime.now(timezone.utc)
        update = TicketUpdate(
            status=TicketStatus.COMPLETED,
            result=result,
            completed_at=now,
        )
        return self.update(ticket_id, update, expected_version=expected_version)

    def mark_awaiting_approval(
        self, ticket_id: UUID, result: dict[str, Any], expected_version: int
    ) -> Ticket:
        update = TicketUpdate(
            status=TicketStatus.AWAITING_APPROVAL,
            result=result,
        )
        return self.update(ticket_id, update, expected_version=expected_version)

    def mark_failed_permanent(
        self, ticket_id: UUID, error: str, expected_version: int
    ) -> Ticket:
        now = datetime.now(timezone.utc)
        update = TicketUpdate(
            status=TicketStatus.FAILED_PERMANENT,
            result={"error": error},
            completed_at=now,
        )
        return self.update(ticket_id, update, expected_version=expected_version)

    def increment_attempt(self, ticket_id: UUID) -> Ticket:
        ticket = self.get_by_id(ticket_id)
        if ticket is None:
            raise TicketNotFoundError(f"Ticket {ticket_id} not found")

        update = TicketUpdate(
            status=TicketStatus.PENDING,
            attempt_count=ticket.attempt_count + 1,
        )
        return self.update(ticket_id, update)


class TicketEventRepository:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create(self, event: TicketEventCreate) -> TicketEvent:
        data = {
            "ticket_id": str(event.ticket_id),
            "event_type": event.event_type.value,
            "step_name": event.step_name,
            "payload": event.payload,
        }
        result = self.client.table("ticket_events").insert(data).execute()
        return TicketEvent(**result.data[0])

    def get_by_ticket_id(self, ticket_id: UUID) -> list[TicketEvent]:
        result = (
            self.client.table("ticket_events")
            .select("*")
            .eq("ticket_id", str(ticket_id))
            .order("created_at", desc=False)
            .execute()
        )
        return [TicketEvent(**row) for row in result.data]

    def log_status_change(
        self, ticket_id: UUID, old_status: TicketStatus, new_status: TicketStatus
    ) -> TicketEvent:
        return self.create(
            TicketEventCreate(
                ticket_id=ticket_id,
                event_type=EventType.STATUS_CHANGE,
                payload={"old_status": old_status.value, "new_status": new_status.value},
            )
        )

    def log_step_complete(
        self, ticket_id: UUID, step_name: str, payload: dict[str, Any] | None = None
    ) -> TicketEvent:
        return self.create(
            TicketEventCreate(
                ticket_id=ticket_id,
                event_type=EventType.STEP_COMPLETE,
                step_name=step_name,
                payload=payload,
            )
        )

    def log_error(
        self, ticket_id: UUID, error: str, step_name: str | None = None
    ) -> TicketEvent:
        return self.create(
            TicketEventCreate(
                ticket_id=ticket_id,
                event_type=EventType.ERROR,
                step_name=step_name,
                payload={"error": error},
            )
        )

    def log_retry(self, ticket_id: UUID, attempt: int, error: str) -> TicketEvent:
        return self.create(
            TicketEventCreate(
                ticket_id=ticket_id,
                event_type=EventType.RETRY,
                payload={"attempt": attempt, "error": error},
            )
        )


class WorkflowCheckpointRepository:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def upsert(self, checkpoint: WorkflowCheckpointUpsert) -> WorkflowCheckpoint:
        data = {
            "ticket_id": str(checkpoint.ticket_id),
            "state": checkpoint.state,
            "current_step": checkpoint.current_step,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = (
            self.client.table("workflow_checkpoints")
            .upsert(data, on_conflict="ticket_id")
            .execute()
        )
        return WorkflowCheckpoint(**result.data[0])

    def get_by_ticket_id(self, ticket_id: UUID) -> WorkflowCheckpoint | None:
        result = (
            self.client.table("workflow_checkpoints")
            .select("*")
            .eq("ticket_id", str(ticket_id))
            .execute()
        )
        if not result.data:
            return None
        return WorkflowCheckpoint(**result.data[0])

    def delete(self, ticket_id: UUID) -> None:
        self.client.table("workflow_checkpoints").delete().eq(
            "ticket_id", str(ticket_id)
        ).execute()


class ApprovalRepository:
    def __init__(self, client: Client | None = None):
        self.client = client or get_supabase_client()

    def create(self, approval: ApprovalRequestCreate) -> ApprovalRequest:
        data = {
            "ticket_id": str(approval.ticket_id),
            "action_type": approval.action_type,
            "action_params": approval.action_params,
            "status": ApprovalStatus.PENDING.value,
        }
        result = self.client.table("approval_requests").insert(data).execute()
        return ApprovalRequest(**result.data[0])

    def get_by_id(self, approval_id: UUID) -> ApprovalRequest | None:
        result = (
            self.client.table("approval_requests")
            .select("*")
            .eq("id", str(approval_id))
            .execute()
        )
        if not result.data:
            return None
        return ApprovalRequest(**result.data[0])

    def get_by_ticket_id(self, ticket_id: UUID) -> list[ApprovalRequest]:
        result = (
            self.client.table("approval_requests")
            .select("*")
            .eq("ticket_id", str(ticket_id))
            .order("requested_at", desc=True)
            .execute()
        )
        return [ApprovalRequest(**row) for row in result.data]

    def get_pending(self) -> list[ApprovalRequest]:
        result = (
            self.client.table("approval_requests")
            .select("*")
            .eq("status", ApprovalStatus.PENDING.value)
            .order("requested_at", desc=False)
            .execute()
        )
        return [ApprovalRequest(**row) for row in result.data]

    def decide(
        self, approval_id: UUID, decision: ApprovalDecision
    ) -> ApprovalRequest | None:
        now = datetime.now(timezone.utc)
        status = ApprovalStatus.APPROVED if decision.approved else ApprovalStatus.REJECTED

        data = {
            "status": status.value,
            "decided_at": now.isoformat(),
            "decided_by": decision.decided_by,
            "decision_reason": decision.reason,
        }

        result = (
            self.client.table("approval_requests")
            .update(data)
            .eq("id", str(approval_id))
            .eq("status", ApprovalStatus.PENDING.value)  # Only update if still pending
            .execute()
        )

        if not result.data:
            return None
        return ApprovalRequest(**result.data[0])
