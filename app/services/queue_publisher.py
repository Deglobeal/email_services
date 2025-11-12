import asyncio
import aio_pika
import json
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("queue_publisher")

async def publish_email(to: str, subject: str, body: str, request_id: str | None = None, priority: int = 1):
    """
    Publish email to RabbitMQ queue
    """
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(settings.exchange_name, aio_pika.ExchangeType.DIRECT) # type: ignore
            message_body = json.dumps({
                "to": to,
                "subject": subject,
                "body": body,
                "request_id": request_id,
                "priority": priority
            }).encode()

            await exchange.publish(
                aio_pika.Message(body=message_body, delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
                routing_key=settings.email_queue_name # type: ignore
            )
            logger.info({"status": "message_published", "to": to, "subject": subject, "request_id": request_id})
    except Exception as e:
        logger.error({"status": "publish_failed", "error": str(e)})
        raise
