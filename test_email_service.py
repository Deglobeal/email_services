import asyncio
import aio_pika
import os
from dotenv import load_dotenv

load_dotenv()

RABBIT_URL = os.getenv("QUEUE_HOST")
EMAIL_QUEUE = os.getenv("EMAIL_QUEUE_NAME", "email.queue")
DLQ = os.getenv("DEAD_LETTER_QUEUE_NAME", "dead_letter.queue")
EXCHANGE = os.getenv("EXCHANGE_NAME", "notifications.direct")

async def reset_queues():
    print(f"🔄 Connecting to {RABBIT_URL}")
    connection = await aio_pika.connect_robust(RABBIT_URL)
    async with connection:
        channel = await connection.channel()

        # Try deleting old queues/exchanges
        print("🗑️ Deleting existing queues (if they exist)...")
        for q in [EMAIL_QUEUE, DLQ]:
            try:
                await channel.queue_delete(q)
                print(f"✅ Deleted queue: {q}")
            except Exception as e:
                print(f"⚠️ Could not delete {q}: {e}")

        try:
            await channel.exchange_delete(EXCHANGE)
            print(f"✅ Deleted exchange: {EXCHANGE}")
        except Exception as e:
            print(f"⚠️ Could not delete exchange: {e}")

        # Recreate fresh
        print("🔧 Creating new exchange and queues...")
        exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.DIRECT, durable=True)
        dlq = await channel.declare_queue(DLQ, durable=True)
        await dlq.bind(exchange, routing_key="failed")

        email_queue = await channel.declare_queue(
            EMAIL_QUEUE,
            durable=True,
            arguments={"x-dead-letter-exchange": "dead.letter.exchange"}
        )
        await email_queue.bind(exchange, routing_key=EMAIL_QUEUE)

        print(f"✅ Recreated {EMAIL_QUEUE} and {DLQ} successfully.")

asyncio.run(reset_queues())
