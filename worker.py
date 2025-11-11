import asyncio
from app.services.queue_consumer import consume
from app.utils.logger import get_logger

logger = get_logger("worker")

if __name__ == "__main__":
    try:
        logger.info("worker_starting")
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("worker_stopped")
