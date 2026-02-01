from typing import Annotated, Any
from uuid import UUID

from langgraph.graph.message import add_messages
from pydantic import BaseModel


class TicketInput(BaseModel):
    ticket_id: UUID
    customer_id: str
    subject: str
    body: str


class WorkflowState(BaseModel):
    """State schema for the ticket processing workflow."""

    # Input
    ticket_id: str
    customer_id: str
    subject: str
    body: str

    # Processing results
    classification: str | None = None
    entities: dict[str, Any] | None = None
    research_results: list[dict[str, Any]] | None = None
    draft_response: str | None = None
    review_notes: str | None = None
    final_response: str | None = None

    # Tracking
    current_step: str = "start"
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True
