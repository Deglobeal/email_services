import asyncio
import aio_pika
import json
from app.utils.logger import get_logger
from app.services.email_service import send_email  # assuming you have this
from app.config import settings  # your config file for RabbitMQ URL, etc.

logger = get_logger(__name__)


async def consume():
    """
    Connect to RabbitMQ and consume email messages asynchronously.
    """
    rabbitmq_url = getattr(settings, "RABBITMQ_URL", "amqp://iE3xhRjkn8bQHL1Z:ZLuWC7X7b5TdmseCa43AN4eB2IWy3dPD@yamanote.proxy.rlwy.net:15031/")

    logger.info({"status": "connecting_to_rabbitmq", "url": rabbitmq_url})

    # Connect to RabbitMQ
    connection = await aio_pika.connect_robust(rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(
            "email.queue",
            durable=True
        )

        logger.info({"status": "started_consuming", "queue": queue.name})

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        body = message.body.decode()
                        data = json.loads(body)
                        logger.info({"received_message": data})

                        # Send email (your async email handler)
                        await send_email(
                            recipient=data.get("to"),
                            subject=data.get("subject"),
                            body=data.get("body"),
                        )

                        logger.info({
                            "status": "email_sent_success",
                            "recipient": data.get("to")
                        })

                    except Exception as e:
                        logger.error({
                            "status": "email_send_failed",
                            "error": str(e),
                            "body": message.body.decode()
                        })
                        # Optionally: requeue or dead-letter here
                        await asyncio.sleep(2)


if __name__ == "__main__":
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        print("\n[⚠️] Consumer stopped manually.")
