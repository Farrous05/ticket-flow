from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.common.config import get_settings
from src.common.logging import get_logger
from src.db.models import (
    ApprovalRequestCreate,
    EventType,
    TicketEventCreate,
    TicketStatus,
    TicketUpdate,
)
from src.db.repositories import (
    ApprovalRepository,
    OptimisticLockError,
    TicketEventRepository,
    TicketNotFoundError,
    TicketRepository,
    WorkflowCheckpointRepository,
)

logger = get_logger(__name__)
settings = get_settings()


class TicketProcessor:
    def __init__(self):
        self.ticket_repo = TicketRepository()
        self.event_repo = TicketEventRepository()
        self.checkpoint_repo = WorkflowCheckpointRepository()
        self.approval_repo = ApprovalRepository()
        self.worker_id = settings.worker_id
        self.use_agent = settings.use_agent_workflow

        # Initialize the appropriate workflow
        if self.use_agent:
            from src.workflow.agent import get_compiled_agent

            self.workflow = get_compiled_agent()
            logger.info("processor_initialized", mode="agent")
        else:
            from src.workflow.graph import get_compiled_workflow

            self.workflow = get_compiled_workflow()
            logger.info("processor_initialized", mode="legacy")

    def process(self, ticket_id: UUID, attempt: int) -> bool:
        """
        Process a ticket through the workflow.

        Returns True if processing completed (success or permanent failure).
        Returns False if processing should be retried.
        """
        logger.info("processing_ticket", ticket_id=str(ticket_id), attempt=attempt)

        # Load ticket
        ticket = self.ticket_repo.get_by_id(ticket_id)
        if ticket is None:
            logger.error("ticket_not_found", ticket_id=str(ticket_id))
            return True  # Ack message, data inconsistency

        # Check if already processed or awaiting approval (idempotency)
        if ticket.status in [
            TicketStatus.COMPLETED,
            TicketStatus.FAILED_PERMANENT,
            TicketStatus.AWAITING_APPROVAL,
        ]:
            logger.info(
                "ticket_already_processed",
                ticket_id=str(ticket_id),
                status=ticket.status.value,
            )
            return True

        # Check for stale processing lock
        if ticket.status == TicketStatus.PROCESSING:
            if ticket.last_heartbeat:
                stale_threshold = settings.stale_processing_threshold_seconds
                age = (datetime.now(timezone.utc) - ticket.last_heartbeat).total_seconds()
                if age < stale_threshold:
                    logger.info(
                        "ticket_being_processed_by_another_worker",
                        ticket_id=str(ticket_id),
                        worker_id=ticket.worker_id,
                    )
                    return False  # Requeue

        # Acquire processing lock
        try:
            ticket = self.ticket_repo.acquire_for_processing(
                ticket_id, self.worker_id, ticket.version
            )
        except OptimisticLockError:
            logger.info("lock_conflict", ticket_id=str(ticket_id))
            return False  # Requeue

        self.event_repo.log_status_change(
            ticket_id, TicketStatus.PENDING, TicketStatus.PROCESSING
        )

        # Load checkpoint if resuming
        checkpoint = self.checkpoint_repo.get_by_ticket_id(ticket_id)
        initial_state: dict[str, Any]

        if checkpoint:
            logger.info(
                "resuming_from_checkpoint",
                ticket_id=str(ticket_id),
                step=checkpoint.current_step,
            )
            initial_state = checkpoint.state
        else:
            initial_state = self._create_initial_state(ticket)

        # Execute workflow
        try:
            final_state = self._execute_workflow(ticket_id, initial_state)

            # Extract result based on workflow type
            result = self._extract_result(final_state)

            # Reload ticket to get current version (heartbeats increment it)
            current_ticket = self.ticket_repo.get_by_id(ticket_id)
            if current_ticket is None:
                raise TicketNotFoundError(f"Ticket {ticket_id} disappeared")

            # Check if workflow is waiting for approval
            pending_approval = result.get("pending_approval")
            if pending_approval:
                # Create approval request
                approval_request = ApprovalRequestCreate(
                    ticket_id=ticket_id,
                    action_type=pending_approval.get("tool", "unknown"),
                    action_params=pending_approval.get("args", {}),
                )
                approval = self.approval_repo.create(approval_request)
                logger.info(
                    "approval_requested",
                    ticket_id=str(ticket_id),
                    approval_id=str(approval.id),
                    action_type=approval.action_type,
                )

                # Mark ticket as awaiting approval
                self.ticket_repo.mark_awaiting_approval(
                    ticket_id, result, current_ticket.version
                )
                self.event_repo.log_status_change(
                    ticket_id, TicketStatus.PROCESSING, TicketStatus.AWAITING_APPROVAL
                )

                # Keep checkpoint for resuming after approval
                logger.info("ticket_awaiting_approval", ticket_id=str(ticket_id))
                return True

            # Normal completion
            self.ticket_repo.mark_completed(ticket_id, result, current_ticket.version)
            self.event_repo.log_status_change(
                ticket_id, TicketStatus.PROCESSING, TicketStatus.COMPLETED
            )

            # Cleanup checkpoint
            self.checkpoint_repo.delete(ticket_id)

            logger.info("ticket_completed", ticket_id=str(ticket_id))
            return True

        except Exception as e:
            logger.error(
                "workflow_error",
                ticket_id=str(ticket_id),
                error=str(e),
            )

            self.event_repo.log_error(ticket_id, str(e))

            # Check if max retries reached
            if attempt >= settings.max_retries:
                # Reload for current version
                current_ticket = self.ticket_repo.get_by_id(ticket_id)
                version = current_ticket.version if current_ticket else 1
                self.ticket_repo.mark_failed_permanent(ticket_id, str(e), version)
                self.event_repo.log_status_change(
                    ticket_id, TicketStatus.PROCESSING, TicketStatus.FAILED_PERMANENT
                )
                logger.error("ticket_failed_permanent", ticket_id=str(ticket_id))
                return True  # Don't retry

            # Increment attempt and requeue
            self.ticket_repo.increment_attempt(ticket_id)
            self.event_repo.log_retry(ticket_id, attempt, str(e))
            return False

    def _create_initial_state(self, ticket) -> dict[str, Any]:
        """Create initial state based on workflow type."""
        if self.use_agent:
            # Agent workflow needs messages
            from langchain_core.messages import HumanMessage, SystemMessage

            from src.workflow.agent import SYSTEM_PROMPT

            ticket_message = f"""## Support Ticket

**Ticket ID:** {ticket.id}
**Customer ID:** {ticket.customer_id}
**Subject:** {ticket.subject}

**Message:**
{ticket.body}

Please analyze this ticket and help resolve the customer's issue."""

            return {
                "ticket_id": str(ticket.id),
                "customer_id": ticket.customer_id,
                "subject": ticket.subject,
                "body": ticket.body,
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=ticket_message),
                ],
                "final_response": None,
                "actions_taken": [],
                "pending_approval": None,
                "should_end": False,
            }
        else:
            # Legacy workflow
            return {
                "ticket_id": str(ticket.id),
                "customer_id": ticket.customer_id,
                "subject": ticket.subject,
                "body": ticket.body,
            }

    def _extract_result(self, final_state: dict[str, Any]) -> dict[str, Any]:
        """Extract result based on workflow type."""
        if self.use_agent:
            return {
                "final_response": final_state.get("final_response"),
                "actions_taken": final_state.get("actions_taken", []),
                "pending_approval": final_state.get("pending_approval"),
            }
        else:
            return {
                "classification": final_state.get("classification"),
                "entities": final_state.get("entities"),
                "final_response": final_state.get("final_response"),
                "review_notes": final_state.get("review_notes"),
            }

    def _execute_workflow(
        self, ticket_id: UUID, initial_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute the workflow with checkpoint persistence."""
        config = {"configurable": {"thread_id": str(ticket_id)}}

        final_state = initial_state

        for event in self.workflow.stream(initial_state, config):
            # event is a dict with node name as key
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    # Merge state carefully for agent workflow
                    if self.use_agent and "messages" in node_output:
                        # Messages need special handling - they accumulate
                        current_messages = final_state.get("messages", [])
                        new_messages = node_output.get("messages", [])
                        final_state = {
                            **final_state,
                            **node_output,
                            "messages": current_messages + list(new_messages),
                        }
                    else:
                        final_state = {**final_state, **node_output}

                    # Save checkpoint (serialize messages for agent)
                    checkpoint_state = self._serialize_state_for_checkpoint(final_state)

                    from src.db.models import WorkflowCheckpointUpsert

                    self.checkpoint_repo.upsert(
                        WorkflowCheckpointUpsert(
                            ticket_id=ticket_id,
                            state=checkpoint_state,
                            current_step=node_output.get("current_step", node_name),
                        )
                    )

                    # Log step completion
                    self.event_repo.log_step_complete(
                        ticket_id,
                        node_name,
                        {"output_keys": list(node_output.keys())},
                    )

                    # Update heartbeat
                    self.ticket_repo.update_heartbeat(ticket_id, self.worker_id)

        return final_state

    def _serialize_state_for_checkpoint(self, state: dict[str, Any]) -> dict[str, Any]:
        """Serialize state for JSON storage in checkpoint."""
        serialized = {}

        for key, value in state.items():
            if key == "messages":
                # Serialize messages to dicts
                serialized[key] = [
                    {
                        "type": type(msg).__name__,
                        "content": msg.content,
                        "additional_kwargs": getattr(msg, "additional_kwargs", {}),
                    }
                    for msg in value
                    if hasattr(msg, "content")
                ]
            else:
                serialized[key] = value

        return serialized
