"""
Email parser service for handling inbound emails from various providers.

Supports SendGrid, Mailgun, Postmark, and generic JSON formats.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from src.common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EmailAttachment:
    """Represents an email attachment."""

    filename: str
    content_type: str
    size: int = 0
    content: bytes | None = None


@dataclass
class ParsedEmail:
    """Normalized email data from any provider."""

    from_email: str
    from_name: str | None = None
    to_email: str | None = None
    subject: str = ""
    body: str = ""
    html: str | None = None
    message_id: str | None = None
    in_reply_to: str | None = None
    references: list[str] = field(default_factory=list)
    attachments: list[EmailAttachment] = field(default_factory=list)
    raw_headers: dict[str, str] = field(default_factory=dict)


class EmailParser:
    """Parser for converting email provider webhooks to normalized format."""

    @staticmethod
    def parse_sendgrid(data: dict[str, Any]) -> ParsedEmail:
        """
        Parse SendGrid Inbound Parse webhook data.

        SendGrid form fields:
        - from: "Name <email@example.com>"
        - to: "support@company.com"
        - subject: "Subject line"
        - text: "Plain text body"
        - html: "<p>HTML body</p>"
        - headers: "Raw email headers"
        - envelope: JSON with routing info
        - attachments: Number of attachments
        - attachment1, attachment2...: File data
        """
        from_field = data.get("from", "")
        from_email, from_name = EmailParser._parse_email_address(from_field)

        # Parse headers for message ID and threading
        headers = EmailParser._parse_headers(data.get("headers", ""))

        # Parse attachments
        attachments = []
        num_attachments = int(data.get("attachments", 0))
        for i in range(1, num_attachments + 1):
            attachment_data = data.get(f"attachment{i}")
            if attachment_data:
                # SendGrid sends as UploadFile
                attachments.append(
                    EmailAttachment(
                        filename=getattr(attachment_data, "filename", f"attachment{i}"),
                        content_type=getattr(
                            attachment_data, "content_type", "application/octet-stream"
                        ),
                    )
                )

        return ParsedEmail(
            from_email=from_email,
            from_name=from_name,
            to_email=data.get("to"),
            subject=data.get("subject", ""),
            body=data.get("text", ""),
            html=data.get("html"),
            message_id=headers.get("message-id"),
            in_reply_to=headers.get("in-reply-to"),
            references=EmailParser._parse_references(headers.get("references", "")),
            attachments=attachments,
            raw_headers=headers,
        )

    @staticmethod
    def parse_mailgun(data: dict[str, Any]) -> ParsedEmail:
        """
        Parse Mailgun webhook data.

        Mailgun fields:
        - sender: "email@example.com"
        - from: "Name <email@example.com>"
        - recipient: "support@company.com"
        - subject: "Subject line"
        - body-plain: "Plain text body"
        - body-html: "<p>HTML body</p>"
        - Message-Id: "<id@mail.example.com>"
        - In-Reply-To: "<previous@mail.example.com>"
        - attachment-count: Number of attachments
        - attachment-x: Attachment data
        """
        from_field = data.get("from", data.get("sender", ""))
        from_email, from_name = EmailParser._parse_email_address(from_field)

        # Parse attachments
        attachments = []
        attachment_count = int(data.get("attachment-count", 0))
        for i in range(1, attachment_count + 1):
            att = data.get(f"attachment-{i}")
            if att:
                attachments.append(
                    EmailAttachment(
                        filename=getattr(att, "filename", f"attachment{i}"),
                        content_type=getattr(
                            att, "content_type", "application/octet-stream"
                        ),
                    )
                )

        return ParsedEmail(
            from_email=from_email,
            from_name=from_name,
            to_email=data.get("recipient"),
            subject=data.get("subject", ""),
            body=data.get("body-plain", data.get("stripped-text", "")),
            html=data.get("body-html", data.get("stripped-html")),
            message_id=data.get("Message-Id"),
            in_reply_to=data.get("In-Reply-To"),
            references=EmailParser._parse_references(data.get("References", "")),
            attachments=attachments,
        )

    @staticmethod
    def parse_postmark(data: dict[str, Any]) -> ParsedEmail:
        """
        Parse Postmark inbound webhook data.

        Postmark JSON fields:
        - From: "email@example.com"
        - FromName: "Sender Name"
        - To: "support@company.com"
        - Subject: "Subject line"
        - TextBody: "Plain text body"
        - HtmlBody: "<p>HTML body</p>"
        - MessageID: "<id@mail.example.com>"
        - ReplyTo: "reply@example.com"
        - Headers: [{Name, Value}]
        - Attachments: [{Name, ContentType, ContentLength, Content}]
        """
        # Extract headers
        headers = {}
        for header in data.get("Headers", []):
            headers[header.get("Name", "").lower()] = header.get("Value", "")

        # Parse attachments
        attachments = []
        for att in data.get("Attachments", []):
            attachments.append(
                EmailAttachment(
                    filename=att.get("Name", "attachment"),
                    content_type=att.get("ContentType", "application/octet-stream"),
                    size=att.get("ContentLength", 0),
                )
            )

        return ParsedEmail(
            from_email=data.get("From", ""),
            from_name=data.get("FromName"),
            to_email=data.get("To"),
            subject=data.get("Subject", ""),
            body=data.get("TextBody", ""),
            html=data.get("HtmlBody"),
            message_id=data.get("MessageID"),
            in_reply_to=headers.get("in-reply-to"),
            references=EmailParser._parse_references(headers.get("references", "")),
            attachments=attachments,
            raw_headers=headers,
        )

    @staticmethod
    def parse_generic(data: dict[str, Any]) -> ParsedEmail:
        """
        Parse generic JSON email format.

        Expected format:
        {
            "from": "customer@example.com" or "Name <email@example.com>",
            "to": "support@company.com",
            "subject": "Subject line",
            "text": "Plain text body",
            "html": "<p>HTML body</p>",
            "message_id": "<unique-id@mail.example.com>",
            "in_reply_to": "<previous-id@mail.example.com>",
            "attachments": [{"filename": "file.pdf", "content_type": "application/pdf"}]
        }
        """
        from_field = data.get("from", "")
        from_email, from_name = EmailParser._parse_email_address(from_field)

        # Parse attachments
        attachments = []
        for att in data.get("attachments", []):
            attachments.append(
                EmailAttachment(
                    filename=att.get("filename", "attachment"),
                    content_type=att.get("content_type", "application/octet-stream"),
                    size=att.get("size", 0),
                )
            )

        return ParsedEmail(
            from_email=from_email,
            from_name=from_name,
            to_email=data.get("to"),
            subject=data.get("subject", ""),
            body=data.get("text", data.get("body", "")),
            html=data.get("html"),
            message_id=data.get("message_id"),
            in_reply_to=data.get("in_reply_to"),
            references=data.get("references", []),
            attachments=attachments,
        )

    @staticmethod
    def _parse_email_address(address: str) -> tuple[str, str | None]:
        """
        Parse email address into email and name components.

        Handles formats like:
        - "email@example.com"
        - "Name <email@example.com>"
        - "<email@example.com>"
        """
        if not address:
            return "", None

        # Match "Name <email>" format
        match = re.match(r'^"?([^"<]*)"?\s*<([^>]+)>$', address.strip())
        if match:
            name = match.group(1).strip() or None
            email = match.group(2).strip()
            return email, name

        # Just an email address
        email = address.strip().strip("<>")
        return email, None

    @staticmethod
    def _parse_headers(headers_str: str) -> dict[str, str]:
        """Parse raw email headers string into dict."""
        headers = {}
        if not headers_str:
            return headers

        current_key = None
        current_value = ""

        for line in headers_str.split("\n"):
            if line.startswith((" ", "\t")) and current_key:
                # Continuation of previous header
                current_value += " " + line.strip()
            elif ":" in line:
                # Save previous header
                if current_key:
                    headers[current_key.lower()] = current_value

                # Start new header
                key, value = line.split(":", 1)
                current_key = key.strip()
                current_value = value.strip()

        # Save last header
        if current_key:
            headers[current_key.lower()] = current_value

        return headers

    @staticmethod
    def _parse_references(references: str) -> list[str]:
        """Parse References header into list of message IDs."""
        if not references:
            return []

        # Extract all <message-id> patterns
        return re.findall(r"<[^>]+>", references)
