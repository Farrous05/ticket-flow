"""
Email ingestion routes for receiving inbound emails as tickets.

Supports webhooks from email providers like SendGrid, Mailgun, and Postmark.
"""

import hashlib
import hmac
from typing import Any
from uuid import UUID, uuid5

from fastapi import APIRouter, Header, HTTPException, Request, status

from src.api.models import CreateTicketResponse
from src.common.config import get_settings
from src.common.logging import get_logger
from src.common.metrics import TICKETS_CREATED
from src.common.queue import QueuePublisher
from src.db.models import EventType, TicketCreate, TicketEventCreate
from src.db.repositories import TicketEventRepository, TicketRepository
from src.services.email_parser import EmailParser, ParsedEmail

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks/email", tags=["email"])

# Namespace UUID for generating deterministic ticket IDs from emails
EMAIL_TICKET_NAMESPACE = UUID("7ba8c920-0ead-22e2-91c5-10d05fe541d9")


def generate_email_ticket_id(message_id: str, from_email: str, subject: str) -> UUID:
    """Generate deterministic ticket ID from email for idempotency."""
    content = f"{message_id}:{from_email}:{subject}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    return uuid5(EMAIL_TICKET_NAMESPACE, content_hash)


@router.post("/inbound/sendgrid", response_model=CreateTicketResponse)
async def receive_sendgrid_email(request: Request) -> CreateTicketResponse:
    """
    Webhook endpoint for SendGrid Inbound Parse.

    SendGrid sends multipart/form-data with email fields.
    Configure at: https://app.sendgrid.com/settings/parse
    """
    try:
        form_data = await request.form()

        parsed = EmailParser.parse_sendgrid(dict(form_data))
        return await _create_ticket_from_email(parsed)

    except Exception as e:
        logger.error("sendgrid_webhook_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse SendGrid email: {str(e)}",
        )


@router.post("/inbound/mailgun", response_model=CreateTicketResponse)
async def receive_mailgun_email(
    request: Request,
    timestamp: str = Header(None, alias="X-Mailgun-Timestamp"),
    token: str = Header(None, alias="X-Mailgun-Token"),
    signature: str = Header(None, alias="X-Mailgun-Signature"),
) -> CreateTicketResponse:
    """
    Webhook endpoint for Mailgun routes.

    Mailgun sends multipart/form-data or JSON based on configuration.
    Configure at: https://app.mailgun.com/app/receiving/routes
    """
    try:
        # Verify signature if webhook signing key is configured
        if settings.mailgun_webhook_key and signature:
            if not _verify_mailgun_signature(timestamp, token, signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Mailgun signature",
                )

        content_type = request.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            form_data = await request.form()
            parsed = EmailParser.parse_mailgun(dict(form_data))
        else:
            json_data = await request.json()
            parsed = EmailParser.parse_mailgun(json_data)

        return await _create_ticket_from_email(parsed)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("mailgun_webhook_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse Mailgun email: {str(e)}",
        )


@router.post("/inbound/postmark", response_model=CreateTicketResponse)
async def receive_postmark_email(request: Request) -> CreateTicketResponse:
    """
    Webhook endpoint for Postmark inbound.

    Postmark sends JSON with email data.
    Configure at: https://account.postmarkapp.com/servers/*/inbound
    """
    try:
        json_data = await request.json()
        parsed = EmailParser.parse_postmark(json_data)
        return await _create_ticket_from_email(parsed)

    except Exception as e:
        logger.error("postmark_webhook_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse Postmark email: {str(e)}",
        )


@router.post("/inbound/generic", response_model=CreateTicketResponse)
async def receive_generic_email(request: Request) -> CreateTicketResponse:
    """
    Generic JSON endpoint for custom email integrations.

    Expected format:
    {
        "from": "customer@example.com",
        "to": "support@company.com",
        "subject": "Help with my order",
        "text": "Plain text body",
        "html": "<p>HTML body</p>",
        "message_id": "<unique-id@mail.example.com>",
        "in_reply_to": "<previous-id@mail.example.com>",
        "attachments": [{"filename": "file.pdf", "content_type": "application/pdf"}]
    }
    """
    try:
        json_data = await request.json()
        parsed = EmailParser.parse_generic(json_data)
        return await _create_ticket_from_email(parsed)

    except Exception as e:
        logger.error("generic_email_webhook_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse email: {str(e)}",
        )


async def _create_ticket_from_email(parsed: ParsedEmail) -> CreateTicketResponse:
    """Create a ticket from a parsed email."""
    ticket_repo = TicketRepository()
    event_repo = TicketEventRepository()
    publisher = QueuePublisher()

    # Check for thread - if this is a reply, try to find existing ticket
    existing_ticket = None
    if parsed.in_reply_to:
        existing_ticket = _find_ticket_by_thread(parsed.in_reply_to)

    if existing_ticket:
        # Add as a follow-up to existing ticket
        logger.info(
            "email_thread_reply",
            ticket_id=str(existing_ticket.id),
            message_id=parsed.message_id,
        )

        event_repo.create(
            TicketEventCreate(
                ticket_id=existing_ticket.id,
                event_type=EventType.STATUS_CHANGE,
                step_name="email_reply_received",
                payload={
                    "message_id": parsed.message_id,
                    "from": parsed.from_email,
                    "subject": parsed.subject,
                    "body_preview": parsed.body[:200] if parsed.body else None,
                },
            )
        )

        return CreateTicketResponse(
            ticket_id=existing_ticket.id,
            status=existing_ticket.status,
        )

    # Generate deterministic ID for idempotency
    ticket_id = generate_email_ticket_id(
        parsed.message_id or "",
        parsed.from_email,
        parsed.subject,
    )

    # Check for existing ticket (duplicate email)
    existing = ticket_repo.get_by_id(ticket_id)
    if existing:
        logger.info("duplicate_email_ticket", ticket_id=str(ticket_id))
        return CreateTicketResponse(
            ticket_id=existing.id,
            status=existing.status,
        )

    # Extract customer ID from email
    customer_id = _extract_customer_id(parsed.from_email)

    # Create ticket with email metadata
    from src.db.client import get_supabase_client

    client = get_supabase_client()
    data = {
        "id": str(ticket_id),
        "customer_id": customer_id,
        "subject": parsed.subject or "(No subject)",
        "body": parsed.body or parsed.html or "(Empty email)",
        "status": "pending",
        "channel": "email",
        "metadata": {
            "message_id": parsed.message_id,
            "from_email": parsed.from_email,
            "from_name": parsed.from_name,
            "to_email": parsed.to_email,
            "in_reply_to": parsed.in_reply_to,
            "attachments": [
                {"filename": a.filename, "content_type": a.content_type}
                for a in parsed.attachments
            ],
        },
    }

    result = client.table("tickets").insert(data).execute()
    ticket = result.data[0]

    # Log creation event
    event_repo.create(
        TicketEventCreate(
            ticket_id=ticket_id,
            event_type=EventType.CREATED,
            payload={
                "channel": "email",
                "from": parsed.from_email,
                "subject": parsed.subject,
                "message_id": parsed.message_id,
            },
        )
    )

    # Publish to queue for processing
    publisher.publish(ticket_id)

    # Record metric
    TICKETS_CREATED.labels(status="created").inc()

    logger.info(
        "email_ticket_created",
        ticket_id=str(ticket_id),
        from_email=parsed.from_email,
        subject=parsed.subject,
    )

    return CreateTicketResponse(
        ticket_id=ticket_id,
        status="pending",
    )


def _find_ticket_by_thread(in_reply_to: str) -> Any | None:
    """Find an existing ticket by thread message ID."""
    from src.db.client import get_supabase_client

    client = get_supabase_client()

    # Search for ticket with matching message_id in metadata
    result = (
        client.table("tickets")
        .select("*")
        .contains("metadata", {"message_id": in_reply_to})
        .limit(1)
        .execute()
    )

    if result.data:
        from src.db.models import Ticket
        return Ticket(**result.data[0])

    return None


def _extract_customer_id(email: str) -> str:
    """Extract or generate a customer ID from an email address."""
    # Use email as customer ID for simplicity
    # In production, you might look up the customer in a CRM
    return email.lower().strip()


def _verify_mailgun_signature(timestamp: str, token: str, signature: str) -> bool:
    """Verify Mailgun webhook signature."""
    if not all([timestamp, token, signature, settings.mailgun_webhook_key]):
        return False

    hmac_digest = hmac.new(
        key=settings.mailgun_webhook_key.encode(),
        msg=f"{timestamp}{token}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, hmac_digest)
