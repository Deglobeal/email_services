import asyncio
import aio_pika
import json
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("queue_publisher")


async def publish_email(
    to: str,
    subject: str,
    body: str,
    request_id: str | None = None,
    priority: int = 1,
):
    """
    Publish email data to RabbitMQ queue on Railway.
    Ensures dead-letter exchange/queue exists and matches existing config.
    """
    try:
        rabbitmq_url = settings.queue_host
        logger.info(f"🔍 Connecting to RabbitMQ at: {rabbitmq_url}")

        # ✅ Connect to RabbitMQ
        connection = await aio_pika.connect_robust(rabbitmq_url)
        async with connection:
            channel = await connection.channel()

            # ✅ Declare dead-letter exchange first
            dead_letter_exchange = await channel.declare_exchange(
                settings.dead_letter_queue_name.replace("_queue", ".exchange"),  # e.g., dead.letter.exchange
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            # ✅ Declare the main queue with dead-letter exchange
            queue = await channel.declare_queue(
                settings.email_queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": dead_letter_exchange.name
                }
            )

            # ✅ Declare dead-letter queue and bind to the DLX
            dead_letter_queue = await channel.declare_queue(
                settings.dead_letter_queue_name,
                durable=True
            )
            await dead_letter_queue.bind(dead_letter_exchange, routing_key=settings.dead_letter_queue_name)

            # ✅ Prepare message payload
            message_body = json.dumps(
                {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "request_id": request_id,
                    "priority": priority,
                }
            ).encode()

            # ✅ Publish message directly to queue
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=settings.email_queue_name,
            )

            logger.info(
                {
                    "status": "message_published",
                    "queue": settings.email_queue_name,
                    "to": to,
                    "subject": subject,
                    "request_id": request_id,
                }
            )
            print(f"✅ Message published successfully to {settings.email_queue_name}")

    except Exception as e:
        error_msg = str(e)
        logger.error(
            {
                "status": "publish_failed",
                "queue": settings.email_queue_name,
                "error": error_msg,
            }
        )
        print(f"❌ Failed to publish message: {error_msg}")
        raise


# ✅ For direct testing
if __name__ == "__main__":
    async def test_publish():
        await publish_email(
            to="test@example.com",
            subject="RabbitMQ Test",
            body="This is a test message from local script.",
            request_id="local-test-001",
        )

    asyncio.run(test_publish())
