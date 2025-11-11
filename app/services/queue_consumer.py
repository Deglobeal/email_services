import asyncio
import json
import traceback
import random
from typing import Dict
import aio_pika
from aio_pika import ExchangeType
from tenacity import retry, wait_exponential, stop_after_attempt, RetryError
from app.config import settings
from app.db import SessionLocal
from app.models import EmailStatus, EmailStatusEnum
from app.services.email_sender import send_email_async
from app.utils.logger import get_logger

logger = get_logger("queue_consumer")

FAILED_QUEUE = "failed.queue"
EMAIL_QUEUE = "email.queue"
EXCHANGE = "notifications.direct"
ROUTING_KEY = "email"

def exponential_backoff_seconds(attempt: int):
    # small jitter + exponential up to cap
    return min(60 * 60, (2 ** attempt) + random.uniform(0, 3))

async def publish_to_failed(channel: aio_pika.Channel, payload: Dict, reason: str):
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.DIRECT, durable=True)
    await exchange.publish(
        aio_pika.Message(body=json.dumps({**payload, "error": reason}).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT),
        routing_key="failed",
    )
    logger.info("published_to_failed_queue", extra={"request_id": payload.get("request_id"), "reason": reason})

async def process_message(message: aio_pika.IncomingMessage):
    async with message.process(requeue=False):
        try:
            payload = json.loads(message.body.decode())
            request_id = payload.get("request_id")
            to_email = payload.get("to_email")
            subject = payload.get("subject")
            body = payload.get("body")
            meta = payload.get("meta", {})

            if not request_id:
                logger.error("missing_request_id", extra={"payload": payload})
                return

            db = SessionLocal()
            try:
                existing = db.query(EmailStatus).filter_by(request_id=request_id).first()
                if existing and existing.status == EmailStatusEnum.sent:
                    logger.info("idempotent_skip_already_sent", extra={"request_id": request_id})
                    return

                if not existing:
                    existing = EmailStatus(
                        request_id=request_id,
                        to_email=to_email,
                        subject=subject,
                        body=body,
                        status=EmailStatusEnum.queued,
                        meta=meta,
                    )
                    db.add(existing)
                    db.commit()
                    db.refresh(existing)

                # mark sending
                existing.status = EmailStatusEnum.sending
                existing.attempt += 1
                db.commit()

                # attempt send with retries
                try:
                    success, error = await retry_send_email(to_email, subject, body, attempt=existing.attempt)
                except RetryError as re:
                    success = False
                    error = str(re)
                if success:
                    existing.status = EmailStatusEnum.sent
                    existing.last_error = None
                    db.commit()
                    logger.info("email_sent_success", extra={"request_id": request_id})
                else:
                    existing.status = EmailStatusEnum.failed if existing.attempt >= settings.max_retry_attempts else EmailStatusEnum.failed
                    existing.last_error = error
                    db.commit()
                    # resurrect channel & dead-letter if final failure
                    if existing.attempt >= settings.max_retry_attempts:
                        # publish to failed.queue via channel param available from outer scope
                        # fallback: we will publish by re-opening a connection
                        conn = await aio_pika.connect_robust(settings.rabbitmq_url)
                        ch = await conn.channel()
                        await publish_to_failed(ch, payload, error)
                        await conn.close()
                        logger.error("moved_to_dead_letter", extra={"request_id": request_id, "error": error})
                return
            finally:
                db.close()
        except Exception as exc:
            logger.error("exception_processing_message", extra={"error": str(exc), "trace": traceback.format_exc()})
            return

@retry(wait=wait_exponential(multiplier=1, min=1, max=60), stop=stop_after_attempt(1))
async def retry_send_email(to_email: str, subject: str, body: str, attempt: int = 1):
    # use send_email_async directly; tenacity handles the retry on this wrapper if needed
    success, error = await send_email_async(to_email, subject, body)
    if not success:
        raise Exception(error or "unknown_send_error")
    return True, None

async def consume():
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=5)
    exchange = await channel.declare_exchange(EXCHANGE, ExchangeType.DIRECT, durable=True)
    # declare queues
    queue = await channel.declare_queue(EMAIL_QUEUE, durable=True)
    await queue.bind(exchange, routing_key=ROUTING_KEY)
    # ensure failed queue exists
    await channel.declare_queue(FAILED_QUEUE, durable=True)
    logger.info("started_consuming", extra={"queue": EMAIL_QUEUE})
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await process_message(message)
