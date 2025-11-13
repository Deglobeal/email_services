import asyncio
from app.config import settings
import aio_pika

async def test_rabbitmq():
    print(f"Using RabbitMQ URL: {settings.queue_host}")
    try:
        connection = await aio_pika.connect_robust(settings.queue_host)
        async with connection:
            channel = await connection.channel()
            print("✅ Connected to RabbitMQ successfully!")

            # Check queue declaration
            queue = await channel.declare_queue(settings.email_queue_name, durable=True)
            print(f"✅ Queue '{queue.name}' is ready.")

            dead_letter_queue = await channel.declare_queue(settings.dead_letter_queue_name, durable=True)
            print(f"✅ Dead-letter queue '{dead_letter_queue.name}' is ready.")

    except Exception as e:
        print(f"❌ RabbitMQ test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_rabbitmq())
