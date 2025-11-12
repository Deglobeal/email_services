import asyncio
import aio_pika
import json
from app.services.email_service import send_email
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("queue_consumer")

# In-memory status tracking
email_status_store = {}

async def consume() -> None:
    connection: aio_pika.abc.AbstractRobustConnection | None = None
    channel: aio_pika.abc.AbstractChannel | None = None
    queue: aio_pika.abc.AbstractQueue | None = None

    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue(settings.email_queue_name, durable=True)
            dead_letter_queue = await channel.declare_queue(settings.dead_letter_queue_name, durable=True)

            logger.info({"status": "started_consuming", "queue": queue.name})

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        data: dict = {}  # define upfront
                        try:
                            data = json.loads(message.body.decode())
                            request_id = data.get("request_id") or data.get("to")
                            email_status_store[request_id] = "pending"

                            recipient = data.get("to")
                            subject = data.get("subject")
                            body = data.get("body")

                            if not recipient or not subject or not body:
                                raise ValueError(f"Missing required email field in message: {data}")

                            await send_email(
                                recipient=recipient,
                                subject=subject,
                                body=body
                            )

                            email_status_store[request_id] = "delivered"
                            logger.info({"status": "email_delivered", "request_id": request_id})
                        except Exception as e:
                            request_id = data.get("request_id") or data.get("to")
                            email_status_store[request_id] = "failed"
                            logger.error({"status": "email_failed", "error": str(e), "request_id": request_id})

                            # send to dead-letter queue
                            try:
                                await channel.default_exchange.publish(
                                    aio_pika.Message(body=message.body),
                                    routing_key=settings.dead_letter_queue_name
                                )
                            except Exception as dlq_error:
                                logger.error({"status": "dlq_failed", "error": str(dlq_error)})

                        await asyncio.sleep(0.01)

    except asyncio.CancelledError:
        logger.info("Consumer cancelled gracefully")
        if channel:
            await channel.close()
        if connection:
            await connection.close()
        raise

    except Exception as e:
        logger.error({"status": "consumer_exception", "error": str(e)})
        raise
