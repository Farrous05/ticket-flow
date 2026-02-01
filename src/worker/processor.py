from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.common.config import get_settings
from src.common.logging import get_logger
from src.db.models import EventType, TicketEventCreate, TicketStatus, TicketUpdate
from src.db.repositories import (
    OptimisticLockError,
    TicketEventRepository,
    TicketNotFoundError,
    TicketRepository,
    WorkflowCheckpointRepository,
)
from src.workflow.graph import get_compiled_workflow
from src.workflow.state import WorkflowState

logger = get_logger(__name__)
settings = get_settings()


class TicketProcessor:
    def __init__(self):
        self.ticket_repo = TicketRepository()
        self.event_repo = TicketEventRepository()
        self.checkpoint_repo = WorkflowCheckpointRepository()
        self.workflow = get_compiled_workflow()
        self.worker_id = settings.worker_id

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

        # Check if already processed (idempotency)
        if ticket.status in [TicketStatus.COMPLETED, TicketStatus.FAILED_PERMANENT]:
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
            initial_state = {
                "ticket_id": str(ticket_id),
                "customer_id": ticket.customer_id,
                "subject": ticket.subject,
                "body": ticket.body,
            }

        # Execute workflow
        try:
            final_state = self._execute_workflow(ticket_id, initial_state)

            # Mark completed
            result = {
                "classification": final_state.get("classification"),
                "entities": final_state.get("entities"),
                "final_response": final_state.get("final_response"),
                "review_notes": final_state.get("review_notes"),
            }

            self.ticket_repo.mark_completed(ticket_id, result, ticket.version)
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
                self.ticket_repo.mark_failed_permanent(
                    ticket_id, str(e), ticket.version
                )
                self.event_repo.log_status_change(
                    ticket_id, TicketStatus.PROCESSING, TicketStatus.FAILED_PERMANENT
                )
                logger.error("ticket_failed_permanent", ticket_id=str(ticket_id))
                return True  # Don't retry

            # Increment attempt and requeue
            self.ticket_repo.increment_attempt(ticket_id)
            self.event_repo.log_retry(ticket_id, attempt, str(e))
            return False

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
                    final_state = {**final_state, **node_output}

                    # Save checkpoint
                    from src.db.models import WorkflowCheckpointUpsert
                    self.checkpoint_repo.upsert(
                        WorkflowCheckpointUpsert(
                            ticket_id=ticket_id,
                            state=final_state,
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
