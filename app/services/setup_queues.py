import asyncio
import aio_pika
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("queue_setup")

async def recreate_queue():
    rabbitmq_url = settings.queue_host
    logger.info(f"🔍 Connecting to RabbitMQ at: {rabbitmq_url}")
    connection = await aio_pika.connect_robust(rabbitmq_url)

    async with connection:
        channel = await connection.channel()

        # Delete existing queue (if exists)
        try:
            await channel.queue_delete(settings.email_queue_name)
            logger.info(f"🗑 Deleted existing queue: {settings.email_queue_name}")
        except Exception as e:
            logger.warning(f"Queue delete skipped: {e}")

        # Declare dead-letter queue first
        await channel.declare_queue(
            settings.dead_letter_queue_name,
            durable=True
        )
        logger.info(f"✅ Dead-letter queue ready: {settings.dead_letter_queue_name}")

        # Recreate main queue with proper dead-letter exchange
        await channel.declare_queue(
            settings.email_queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": settings.dead_letter_queue_name}
        )
        logger.info(f"✅ Queue recreated with DLX: {settings.email_queue_name}")

    logger.info("All queues are properly set up.")

if __name__ == "__main__":
    asyncio.run(recreate_queue())
