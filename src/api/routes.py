import hashlib
from uuid import UUID, uuid5

from fastapi import APIRouter, HTTPException, status

from src.api.models import (
    CreateTicketRequest,
    CreateTicketResponse,
    HealthResponse,
    TicketEventResponse,
    TicketResponse,
)
from src.common.logging import get_logger
from src.common.queue import QueueConnection, QueuePublisher
from src.db.client import get_supabase_client
from src.db.models import EventType, TicketCreate, TicketEventCreate, TicketStatus
from src.db.repositories import TicketEventRepository, TicketRepository

logger = get_logger(__name__)

router = APIRouter()

# Namespace UUID for generating deterministic ticket IDs
TICKET_NAMESPACE = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def generate_ticket_id(customer_id: str, subject: str, body: str) -> UUID:
    """Generate deterministic ticket ID for idempotency."""
    content = f"{customer_id}:{subject}:{body}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return uuid5(TICKET_NAMESPACE, content_hash)


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

    logger.info("ticket_created", ticket_id=str(ticket_id))

    return CreateTicketResponse(
        ticket_id=ticket.id,
        status=ticket.status,
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
