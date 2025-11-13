import asyncio
import aio_pika
from app.config import settings

async def reset_queues():
    print(f"Connecting to RabbitMQ: {settings.queue_host}")
    connection = await aio_pika.connect_robust(settings.queue_host)
    async with connection:
        channel = await connection.channel()
        
        # Delete existing queues (if any)
        try:
            await channel.queue_delete(settings.email_queue_name)
            print(f"Deleted existing queue: {settings.email_queue_name}")
        except Exception as e:
            print(f"No existing queue to delete: {settings.email_queue_name} ({e})")

        try:
            await channel.queue_delete(settings.dead_letter_queue_name)
            print(f"Deleted existing queue: {settings.dead_letter_queue_name}")
        except Exception as e:
            print(f"No existing queue to delete: {settings.dead_letter_queue_name} ({e})")

        # Recreate dead-letter queue (just durable)
        await channel.declare_queue(
            settings.dead_letter_queue_name,
            durable=True
        )
        print(f"Created dead-letter queue: {settings.dead_letter_queue_name}")

        # Recreate main queue with dead-letter exchange
        await channel.declare_queue(
            settings.email_queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange": settings.dead_letter_queue_name
            },
        )
        print(f"Created main queue with DLX: {settings.email_queue_name}")

    print("✅ Queue reset complete!")

if __name__ == "__main__":
    asyncio.run(reset_queues())
