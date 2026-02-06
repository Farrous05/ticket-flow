import hashlib
from typing import Optional
from uuid import UUID, uuid5

from fastapi import APIRouter, HTTPException, Query, status

from src.api.models import (
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    ApprovalRequestResponse,
    CreateTicketRequest,
    CreateTicketResponse,
    DashboardStatsResponse,
    HealthResponse,
    TicketEventResponse,
    TicketListResponse,
    TicketResponse,
)
from src.common.logging import get_logger
from src.common.metrics import TICKETS_CREATED
from src.common.queue import QueueConnection, QueuePublisher
from src.db.client import get_supabase_client
from src.db.models import (
    ApprovalDecision,
    ApprovalStatus,
    EventType,
    TicketCreate,
    TicketEventCreate,
    TicketStatus,
)
from src.db.repositories import (
    ApprovalRepository,
    TicketEventRepository,
    TicketRepository,
)

logger = get_logger(__name__)

router = APIRouter()

# Namespace UUID for generating deterministic ticket IDs
TICKET_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def generate_ticket_id(customer_id: str, subject: str, body: str) -> UUID:
    """Generate deterministic ticket ID for idempotency."""
    content = f"{customer_id}:{subject}:{body}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return uuid5(TICKET_NAMESPACE, content_hash)


# --- Ticket Endpoints ---


@router.post(
    "/tickets",
    response_model=CreateTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(request: CreateTicketRequest) -> CreateTicketResponse:
    ticket_repo = TicketRepository()
    event_repo = TicketEventRepository()
    publisher = QueuePublisher()

    ticket_id = generate_ticket_id(
        request.customer_id, request.subject, request.body
    )

    # Check for existing ticket (idempotency)
    existing = ticket_repo.get_by_id(ticket_id)
    if existing:
        logger.info("duplicate_ticket_request", ticket_id=str(ticket_id))
        return CreateTicketResponse(
            ticket_id=existing.id,
            status=existing.status,
        )

    # Create ticket
    ticket = ticket_repo.create(
        TicketCreate(
            id=ticket_id,
            customer_id=request.customer_id,
            subject=request.subject,
            body=request.body,
        )
    )

    # Log creation event
    event_repo.create(
        TicketEventCreate(
            ticket_id=ticket_id,
            event_type=EventType.CREATED,
            payload={
                "customer_id": request.customer_id,
                "subject": request.subject,
            },
        )
    )

    # Publish to queue
    publisher.publish(ticket_id)

    # Record metric
    TICKETS_CREATED.labels(status="created").inc()

    logger.info("ticket_created", ticket_id=str(ticket_id))

    return CreateTicketResponse(
        ticket_id=ticket.id,
        status=ticket.status,
    )


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[TicketStatus] = Query(None, alias="status"),
) -> TicketListResponse:
    """List tickets with pagination and optional status filter."""
    client = get_supabase_client()

    # Build query
    query = client.table("tickets").select("*", count="exact")

    if status_filter:
        query = query.eq("status", status_filter.value)

    # Get total count and paginated results
    offset = (page - 1) * page_size
    result = (
        query.order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    tickets = [
        TicketResponse(
            id=t["id"],
            customer_id=t["customer_id"],
            subject=t["subject"],
            body=t["body"],
            status=t["status"],
            result=t.get("result"),
            attempt_count=t["attempt_count"],
            created_at=t["created_at"],
            started_at=t.get("started_at"),
            completed_at=t.get("completed_at"),
            channel=t.get("channel"),
            metadata=t.get("metadata"),
        )
        for t in result.data
    ]

    return TicketListResponse(
        tickets=tickets,
        total=result.count or len(tickets),
        page=page,
        page_size=page_size,
    )


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: UUID) -> TicketResponse:
    ticket_repo = TicketRepository()
    ticket = ticket_repo.get_by_id(ticket_id)

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    return TicketResponse(
        id=ticket.id,
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        body=ticket.body,
        status=ticket.status,
        result=ticket.result,
        attempt_count=ticket.attempt_count,
        created_at=ticket.created_at,
        started_at=ticket.started_at,
        completed_at=ticket.completed_at,
    )


@router.get("/tickets/{ticket_id}/events", response_model=list[TicketEventResponse])
def get_ticket_events(ticket_id: UUID) -> list[TicketEventResponse]:
    ticket_repo = TicketRepository()
    event_repo = TicketEventRepository()

    # Verify ticket exists
    if not ticket_repo.exists(ticket_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found",
        )

    events = event_repo.get_by_ticket_id(ticket_id)
    return [
        TicketEventResponse(
            id=e.id,
            event_type=e.event_type,
            step_name=e.step_name,
            payload=e.payload,
            created_at=e.created_at,
        )
        for e in events
    ]


# --- Approval Endpoints ---


@router.get("/approvals", response_model=list[ApprovalRequestResponse])
def list_pending_approvals() -> list[ApprovalRequestResponse]:
    """Get all pending approval requests."""
    approval_repo = ApprovalRepository()
    approvals = approval_repo.get_pending()

    return [
        ApprovalRequestResponse(
            id=a.id,
            ticket_id=a.ticket_id,
            action_type=a.action_type,
            action_params=a.action_params,
            status=a.status,
            requested_at=a.requested_at,
            decided_at=a.decided_at,
            decided_by=a.decided_by,
            decision_reason=a.decision_reason,
        )
        for a in approvals
    ]


@router.get("/approvals/{approval_id}", response_model=ApprovalRequestResponse)
def get_approval(approval_id: UUID) -> ApprovalRequestResponse:
    """Get a specific approval request."""
    approval_repo = ApprovalRepository()
    approval = approval_repo.get_by_id(approval_id)

    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )

    return ApprovalRequestResponse(
        id=approval.id,
        ticket_id=approval.ticket_id,
        action_type=approval.action_type,
        action_params=approval.action_params,
        status=approval.status,
        requested_at=approval.requested_at,
        decided_at=approval.decided_at,
        decided_by=approval.decided_by,
        decision_reason=approval.decision_reason,
    )


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalDecisionResponse)
def decide_approval(
    approval_id: UUID,
    decision: ApprovalDecisionRequest,
) -> ApprovalDecisionResponse:
    """Approve or reject an approval request."""
    approval_repo = ApprovalRepository()
    event_repo = TicketEventRepository()

    # Get the approval request
    approval = approval_repo.get_by_id(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found",
        )

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval request already {approval.status.value}",
        )

    # Record the decision
    updated = approval_repo.decide(
        approval_id,
        ApprovalDecision(
            approved=decision.approved,
            decided_by=decision.decided_by,
            reason=decision.reason,
        ),
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval was modified by another process",
        )

    # Log the decision
    event_repo.create(
        TicketEventCreate(
            ticket_id=approval.ticket_id,
            event_type=EventType.STATUS_CHANGE,
            step_name="approval_decision",
            payload={
                "approval_id": str(approval_id),
                "action_type": approval.action_type,
                "approved": decision.approved,
                "decided_by": decision.decided_by,
                "reason": decision.reason,
            },
        )
    )

    action_executed = False
    message = ""
    ticket_repo = TicketRepository()

    # Get the current ticket to update it
    ticket = ticket_repo.get_by_id(approval.ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {approval.ticket_id} not found",
        )

    if decision.approved:
        # Execute the pending action
        try:
            action_executed = _execute_approved_action(
                approval.action_type,
                approval.action_params,
            )
            message = f"Action '{approval.action_type}' approved and executed"

            # Update ticket result with executed action
            result = ticket.result or {}
            result["final_response"] = f"Your {approval.action_type.replace('_', ' ')} request has been approved and processed."
            result["actions_taken"] = result.get("actions_taken", []) + [
                {"tool": approval.action_type, "args": approval.action_params, "approved": True}
            ]
            result["pending_approval"] = None  # Clear pending approval

            # Mark ticket as completed
            ticket_repo.mark_completed(approval.ticket_id, result, ticket.version)
            event_repo.log_status_change(
                approval.ticket_id, TicketStatus.AWAITING_APPROVAL, TicketStatus.COMPLETED
            )

            logger.info(
                "approval_action_executed",
                approval_id=str(approval_id),
                ticket_id=str(approval.ticket_id),
                action_type=approval.action_type,
            )
        except Exception as e:
            logger.error(
                "approval_action_failed",
                approval_id=str(approval_id),
                error=str(e),
            )
            message = f"Action approved but execution failed: {str(e)}"
    else:
        message = f"Action '{approval.action_type}' rejected"

        # Update ticket result with rejection
        result = ticket.result or {}
        result["final_response"] = f"Your {approval.action_type.replace('_', ' ')} request was reviewed but not approved. Reason: {decision.reason or 'No reason provided'}"
        result["pending_approval"] = None  # Clear pending approval

        # Mark ticket as completed (rejected requests are still completed)
        ticket_repo.mark_completed(approval.ticket_id, result, ticket.version)
        event_repo.log_status_change(
            approval.ticket_id, TicketStatus.AWAITING_APPROVAL, TicketStatus.COMPLETED
        )

        logger.info(
            "approval_rejected",
            approval_id=str(approval_id),
            ticket_id=str(approval.ticket_id),
            action_type=approval.action_type,
            reason=decision.reason,
        )

    return ApprovalDecisionResponse(
        approval_id=approval_id,
        ticket_id=approval.ticket_id,
        status=updated.status,
        action_executed=action_executed,
        message=message,
    )


def _execute_approved_action(action_type: str, action_params: dict) -> bool:
    """Execute an approved action."""
    from src.workflow.tools import (
        process_refund,
    )

    if action_type == "process_refund":
        result = process_refund.invoke(action_params)
        return result.get("success", False)

    logger.warning("unknown_action_type", action_type=action_type)
    return False


# --- Dashboard Endpoints ---


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats() -> DashboardStatsResponse:
    """Get dashboard statistics."""
    client = get_supabase_client()
    approval_repo = ApprovalRepository()

    # Get ticket counts by status
    tickets_result = client.table("tickets").select("status").execute()
    tickets = tickets_result.data

    status_counts = {
        "pending": 0,
        "processing": 0,
        "awaiting_approval": 0,
        "completed": 0,
        "failed_permanent": 0,
    }

    for t in tickets:
        status = t["status"]
        if status in status_counts:
            status_counts[status] += 1

    # Get pending approvals count
    pending_approvals = len(approval_repo.get_pending())

    return DashboardStatsResponse(
        total_tickets=len(tickets),
        pending_tickets=status_counts["pending"],
        processing_tickets=status_counts["processing"],
        awaiting_approval_tickets=status_counts["awaiting_approval"],
        completed_tickets=status_counts["completed"],
        failed_tickets=status_counts["failed_permanent"],
        pending_approvals=pending_approvals,
    )


# --- Health Endpoint ---


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    db_status = "healthy"
    queue_status = "healthy"

    # Check database
    try:
        client = get_supabase_client()
        client.table("tickets").select("id").limit(1).execute()
    except Exception as e:
        logger.error("health_check_db_error", error=str(e))
        db_status = "unhealthy"

    # Check queue
    try:
        conn = QueueConnection()
        conn.connect()
        conn.close()
    except Exception as e:
        logger.error("health_check_queue_error", error=str(e))
        queue_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" and queue_status == "healthy" else "unhealthy"

    return HealthResponse(
        status=overall,
        database=db_status,
        queue=queue_status,
    )
