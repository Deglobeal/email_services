import asyncio
import aio_pika
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("rabbitmq_client")

async def get_rabbitmq_connection():
    try:
        connection = await aio_pika.connect_robust(settings.queue_host)
        logger.info("Connected to RabbitMQ successfully")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise
