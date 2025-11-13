# test_rabbitmq_connection.py
import asyncio
import aio_pika
from app.config import settings

async def test_rabbitmq():
    print(f"🔍 Connecting to: {settings.queue_host}")
    try:
        connection = await aio_pika.connect_robust(settings.queue_host)
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(settings.email_queue_name, durable=True)
            print("✅ RabbitMQ connection successful and queue declared!")
    except Exception as e:
        print("❌ RabbitMQ connection failed:", e)

asyncio.run(test_rabbitmq())
