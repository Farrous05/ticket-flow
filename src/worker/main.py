import signal
import sys

from src.common.logging import get_logger, setup_logging
from src.common.queue import QueueConsumer, QueueMessage, QueuePublisher
from src.common.config import get_settings
from src.worker.processor import TicketProcessor

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


def main() -> None:
    logger.info("worker_starting", worker_id=settings.worker_id)

    consumer = QueueConsumer()
    publisher = QueuePublisher()
    processor = TicketProcessor()

    def handle_shutdown(signum: int, frame) -> None:
        logger.info("shutdown_signal_received", signal=signum)
        consumer.stop()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    def process_message(
        message: QueueMessage,
        ack: callable,
        nack: callable,
    ) -> None:
        try:
            completed = processor.process(message.ticket_id, message.attempt)

            if completed:
                ack()
            else:
                # Requeue with incremented attempt
                if message.attempt < settings.max_retries:
                    publisher.publish(message.ticket_id, message.attempt + 1)
                    ack()  # Ack original, new message published
                else:
                    nack(requeue=False)  # Send to DLX
        except Exception as e:
            logger.error(
                "message_handler_error",
                ticket_id=str(message.ticket_id),
                error=str(e),
            )
            nack(requeue=message.attempt < settings.max_retries)

    try:
        consumer.consume(process_message)
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt")
    finally:
        logger.info("worker_stopped")


if __name__ == "__main__":
    main()
