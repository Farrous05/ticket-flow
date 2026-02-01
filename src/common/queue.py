import json
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.spec import Basic, BasicProperties

from src.common.config import get_settings
from src.common.logging import get_logger

logger = get_logger(__name__)


class QueueMessage:
    def __init__(self, ticket_id: UUID, attempt: int, enqueued_at: datetime):
        self.ticket_id = ticket_id
        self.attempt = attempt
        self.enqueued_at = enqueued_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": str(self.ticket_id),
            "attempt": self.attempt,
            "enqueued_at": self.enqueued_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QueueMessage":
        return cls(
            ticket_id=UUID(data["ticket_id"]),
            attempt=data["attempt"],
            enqueued_at=datetime.fromisoformat(data["enqueued_at"]),
        )

    def to_bytes(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> "QueueMessage":
        return cls.from_dict(json.loads(data.decode("utf-8")))


class QueueConnection:
    def __init__(self, url: str | None = None):
        settings = get_settings()
        self.url = url or settings.rabbitmq_url
        self.queue_name = settings.queue_name
        self.dlx_name = settings.dlx_name
        self.prefetch_count = settings.prefetch_count
        self._connection: pika.BlockingConnection | None = None
        self._channel: BlockingChannel | None = None

    def connect(self) -> None:
        if self._connection is not None and self._connection.is_open:
            return

        logger.info("connecting_to_rabbitmq", url=self.url)
        parameters = pika.URLParameters(self.url)
        self._connection = pika.BlockingConnection(parameters)
        self._channel = self._connection.channel()
        self._setup_queues()
        logger.info("rabbitmq_connected")

    def _setup_queues(self) -> None:
        if self._channel is None:
            raise RuntimeError("Channel not initialized")

        # Declare dead letter exchange
        self._channel.exchange_declare(
            exchange=self.dlx_name,
            exchange_type="direct",
            durable=True,
        )

        # Declare dead letter queue
        self._channel.queue_declare(
            queue=f"{self.queue_name}_dead",
            durable=True,
        )
        self._channel.queue_bind(
            queue=f"{self.queue_name}_dead",
            exchange=self.dlx_name,
            routing_key=self.queue_name,
        )

        # Declare main queue with DLX
        self._channel.queue_declare(
            queue=self.queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": self.dlx_name,
                "x-dead-letter-routing-key": self.queue_name,
            },
        )

    def close(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
            logger.info("rabbitmq_disconnected")

    @property
    def channel(self) -> BlockingChannel:
        if self._channel is None:
            self.connect()
        return self._channel  # type: ignore


class QueuePublisher:
    def __init__(self, connection: QueueConnection | None = None):
        self.connection = connection or QueueConnection()

    def publish(self, ticket_id: UUID, attempt: int = 1) -> None:
        message = QueueMessage(
            ticket_id=ticket_id,
            attempt=attempt,
            enqueued_at=datetime.now(timezone.utc),
        )

        self.connection.connect()
        self.connection.channel.basic_publish(
            exchange="",
            routing_key=self.connection.queue_name,
            body=message.to_bytes(),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                content_type="application/json",
            ),
        )

        logger.info(
            "message_published",
            ticket_id=str(ticket_id),
            attempt=attempt,
            queue=self.connection.queue_name,
        )


class QueueConsumer:
    def __init__(self, connection: QueueConnection | None = None):
        self.connection = connection or QueueConnection()
        self._should_stop = False

    def consume(
        self,
        callback: Callable[[QueueMessage, Callable[[], None], Callable[[bool], None]], None],
    ) -> None:
        """
        Start consuming messages from the queue.

        Args:
            callback: Function called for each message. Receives:
                - message: The QueueMessage
                - ack: Function to acknowledge the message
                - nack: Function to reject the message (pass requeue=True to requeue)
        """
        self.connection.connect()
        channel = self.connection.channel
        channel.basic_qos(prefetch_count=self.connection.prefetch_count)

        def on_message(
            ch: BlockingChannel,
            method: Basic.Deliver,
            properties: BasicProperties,
            body: bytes,
        ) -> None:
            delivery_tag = method.delivery_tag

            def ack() -> None:
                ch.basic_ack(delivery_tag=delivery_tag)

            def nack(requeue: bool = False) -> None:
                ch.basic_nack(delivery_tag=delivery_tag, requeue=requeue)

            try:
                message = QueueMessage.from_bytes(body)
                logger.info(
                    "message_received",
                    ticket_id=str(message.ticket_id),
                    attempt=message.attempt,
                )
                callback(message, ack, nack)
            except Exception as e:
                logger.error("message_processing_error", error=str(e))
                nack(requeue=False)

        channel.basic_consume(
            queue=self.connection.queue_name,
            on_message_callback=on_message,
            auto_ack=False,
        )

        logger.info("consumer_started", queue=self.connection.queue_name)

        while not self._should_stop:
            self.connection._connection.process_data_events(time_limit=1)  # type: ignore

    def stop(self) -> None:
        self._should_stop = True
        logger.info("consumer_stopping")
