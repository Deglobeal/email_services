import asyncio
import aio_pika
import json
from app.services.email_service import send_email
from app.config import settings
from app.utils.logger import get_logger
from aio_pika.exceptions import ChannelInvalidStateError

logger = get_logger("queue_consumer")

# In-memory status tracking
email_status_store = {}

async def consume():
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(settings.email_queue_name, durable=True)  # type: ignore
            dead_letter_queue = await channel.declare_queue(settings.dead_letter_queue_name, durable=True)  # type: ignore
            logger.info({"status": "started_consuming", "queue": queue.name})

            try:
                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            try:
                                data = json.loads(message.body.decode())
                                request_id = data.get("request_id") or data.get("to")
                                email_status_store[request_id] = "pending"

                                await send_email(
                                    recipient=data.get("to"),
                                    subject=data.get("subject"),
                                    body=data.get("body")
                                )

                                email_status_store[request_id] = "delivered"
                                logger.info({"status": "email_delivered", "request_id": request_id})

                            except Exception as e:
                                request_id = data.get("request_id") or data.get("to")  # type: ignore
                                email_status_store[request_id] = "failed"
                                logger.error({"status": "email_failed", "error": str(e), "request_id": request_id})

                                # Send to dead-letter queue
                                await channel.default_exchange.publish(
                                    aio_pika.Message(body=message.body),
                                    routing_key=settings.dead_letter_queue_name  # type: ignore
                                )
                                await asyncio.sleep(1)

            except (asyncio.CancelledError, ChannelInvalidStateError):
                logger.info("Consumer stopped gracefully")

    except Exception as e:
        logger.error({"status": "consumer_error", "error": str(e)})

if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
