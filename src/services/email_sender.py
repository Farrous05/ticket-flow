"""
Email sender service for sending responses back to customers.

Supports SendGrid, Mailgun, and SMTP backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from src.common.config import get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class EmailMessage:
    """Email message to send."""

    to: str
    subject: str
    body: str
    html: str | None = None
    reply_to: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    in_reply_to: str | None = None  # For threading
    references: list[str] | None = None  # For threading


class EmailSender(ABC):
    """Abstract base class for email senders."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> dict[str, Any]:
        """Send an email and return the result."""
        pass


class SendGridSender(EmailSender):
    """SendGrid email sender."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.sendgrid.com/v3/mail/send"

    async def send(self, message: EmailMessage) -> dict[str, Any]:
        """Send email via SendGrid API."""
        from_email = message.from_email or settings.email_from_address
        from_name = message.from_name or settings.email_from_name

        payload = {
            "personalizations": [{"to": [{"email": message.to}]}],
            "from": {"email": from_email, "name": from_name},
            "subject": message.subject,
            "content": [{"type": "text/plain", "value": message.body}],
        }

        if message.html:
            payload["content"].append({"type": "text/html", "value": message.html})

        if message.reply_to:
            payload["reply_to"] = {"email": message.reply_to}

        # Add threading headers
        headers = {}
        if message.in_reply_to:
            headers["In-Reply-To"] = message.in_reply_to
        if message.references:
            headers["References"] = " ".join(message.references)
        if headers:
            payload["headers"] = headers

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code in (200, 202):
                logger.info(
                    "sendgrid_email_sent",
                    to=message.to,
                    subject=message.subject,
                )
                return {"success": True, "provider": "sendgrid"}
            else:
                logger.error(
                    "sendgrid_email_failed",
                    status=response.status_code,
                    response=response.text,
                )
                return {
                    "success": False,
                    "provider": "sendgrid",
                    "error": response.text,
                }


class MailgunSender(EmailSender):
    """Mailgun email sender."""

    def __init__(self, api_key: str, domain: str):
        self.api_key = api_key
        self.domain = domain
        self.api_url = f"https://api.mailgun.net/v3/{domain}/messages"

    async def send(self, message: EmailMessage) -> dict[str, Any]:
        """Send email via Mailgun API."""
        from_email = message.from_email or settings.email_from_address
        from_name = message.from_name or settings.email_from_name
        from_field = f"{from_name} <{from_email}>" if from_name else from_email

        data = {
            "from": from_field,
            "to": message.to,
            "subject": message.subject,
            "text": message.body,
        }

        if message.html:
            data["html"] = message.html

        if message.reply_to:
            data["h:Reply-To"] = message.reply_to

        # Add threading headers
        if message.in_reply_to:
            data["h:In-Reply-To"] = message.in_reply_to
        if message.references:
            data["h:References"] = " ".join(message.references)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                data=data,
                auth=("api", self.api_key),
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(
                    "mailgun_email_sent",
                    to=message.to,
                    subject=message.subject,
                    message_id=result.get("id"),
                )
                return {
                    "success": True,
                    "provider": "mailgun",
                    "message_id": result.get("id"),
                }
            else:
                logger.error(
                    "mailgun_email_failed",
                    status=response.status_code,
                    response=response.text,
                )
                return {
                    "success": False,
                    "provider": "mailgun",
                    "error": response.text,
                }


class MockEmailSender(EmailSender):
    """Mock email sender for development/testing."""

    async def send(self, message: EmailMessage) -> dict[str, Any]:
        """Log email instead of sending."""
        logger.info(
            "mock_email_sent",
            to=message.to,
            subject=message.subject,
            body_preview=message.body[:100] if message.body else None,
        )
        return {
            "success": True,
            "provider": "mock",
            "message": "Email logged (mock mode)",
        }


def get_email_sender() -> EmailSender:
    """Get the configured email sender."""
    provider = settings.email_provider

    if provider == "sendgrid" and settings.sendgrid_api_key:
        return SendGridSender(settings.sendgrid_api_key)
    elif provider == "mailgun" and settings.mailgun_api_key:
        return MailgunSender(settings.mailgun_api_key, settings.mailgun_domain)
    else:
        # Default to mock sender for development
        logger.warning("using_mock_email_sender")
        return MockEmailSender()


async def send_ticket_response(
    ticket_id: str,
    response_text: str,
    response_html: str | None = None,
) -> dict[str, Any]:
    """
    Send the agent's response back to the customer via email.

    Args:
        ticket_id: The ticket ID
        response_text: Plain text response
        response_html: Optional HTML response

    Returns:
        Dict with send result
    """
    from src.db.client import get_supabase_client

    client = get_supabase_client()

    # Get ticket with metadata
    result = client.table("tickets").select("*").eq("id", ticket_id).execute()

    if not result.data:
        logger.error("ticket_not_found_for_email", ticket_id=ticket_id)
        return {"success": False, "error": "Ticket not found"}

    ticket = result.data[0]

    # Only send email responses for email channel tickets
    if ticket.get("channel") != "email":
        logger.info("skip_email_response_non_email_channel", ticket_id=ticket_id)
        return {"success": True, "skipped": True, "reason": "Not an email ticket"}

    metadata = ticket.get("metadata", {})
    customer_email = metadata.get("from_email")

    if not customer_email:
        logger.error("no_customer_email", ticket_id=ticket_id)
        return {"success": False, "error": "No customer email in metadata"}

    # Build response email
    sender = get_email_sender()

    # Create reply subject
    original_subject = ticket.get("subject", "")
    if not original_subject.lower().startswith("re:"):
        subject = f"Re: {original_subject}"
    else:
        subject = original_subject

    # Build threading references
    message_id = metadata.get("message_id")
    references = [message_id] if message_id else []
    if metadata.get("in_reply_to"):
        references.insert(0, metadata["in_reply_to"])

    # Create reply-to address with ticket ID for tracking
    reply_to = f"support+{ticket_id}@{settings.email_domain}" if settings.email_domain else None

    message = EmailMessage(
        to=customer_email,
        subject=subject,
        body=response_text,
        html=response_html,
        reply_to=reply_to,
        in_reply_to=message_id,
        references=references if references else None,
    )

    result = await sender.send(message)

    if result.get("success"):
        # Log the response in ticket events
        from src.db.models import EventType, TicketEventCreate
        from src.db.repositories import TicketEventRepository

        event_repo = TicketEventRepository()
        event_repo.create(
            TicketEventCreate(
                ticket_id=ticket_id,
                event_type=EventType.STATUS_CHANGE,
                step_name="email_response_sent",
                payload={
                    "to": customer_email,
                    "subject": subject,
                    "provider": result.get("provider"),
                },
            )
        )

    return result
