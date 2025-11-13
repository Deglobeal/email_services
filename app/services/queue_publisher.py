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
    - Always uses the existing queue's dead-letter exchange if present.
    """
    try:
        rabbitmq_url = settings.queue_host
        logger.info(f"🔍 Connecting to RabbitMQ at: {rabbitmq_url}")

        connection = await aio_pika.connect_robust(rabbitmq_url)
        async with connection:
            channel = await connection.channel()

            # Declare queue idempotently (will not fail if exists)
            await channel.declare_queue(
                settings.email_queue_name,
                durable=True,
                arguments={"x-dead-letter-exchange": "dead.letter.exchange"},
            )

            message_body = json.dumps(
                {
                    "to": to,
                    "subject": subject,
                    "body": body,
                    "request_id": request_id,
                    "priority": priority,
                }
            ).encode()

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


# Direct test
if __name__ == "__main__":
    async def test_publish():
        await publish_email(
            to="test@example.com",
            subject="RabbitMQ Test",
            body="This is a test message from local script.",
            request_id="local-test-003",
        )

    asyncio.run(test_publish())
