from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import EmailRequest, StandardResponse
from app.config import settings
from app.utils.logger import get_logger
import asyncio
import aio_pika
import json

logger = get_logger("main")
app = FastAPI(title="email_service", version="1.0")

@app.get("/health", response_model=StandardResponse)
def health():
    return JSONResponse({"success": True, "message": "email service healthy", "data": {}, "meta": {}})

@app.post("/publish_email", response_model=StandardResponse)
async def publish_email(payload: EmailRequest):
    """
    Accepts an EmailRequest and publishes it to RabbitMQ 'notifications.direct' exchange with routing_key 'email'.
    This endpoint is a helper to test and to be used by API Gateway.
    """
    # validate minimal fields
    if not payload.request_id:
        raise HTTPException(status_code=400, detail="request_id required")

    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        channel = await connection.channel()
        exchange = await channel.declare_exchange("notifications.direct", aio_pika.ExchangeType.DIRECT, durable=True)
        message = aio_pika.Message(body=json.dumps(payload.dict()).encode(), delivery_mode=aio_pika.DeliveryMode.PERSISTENT)
        await exchange.publish(message, routing_key="email")
        await connection.close()
        logger.info("published_email_message", extra={"request_id": payload.request_id, "to": payload.to_email})
        return {"success": True, "message": "published", "data": {"request_id": payload.request_id}, "meta": {}}
    except Exception as exc:
        logger.error("publish_error", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail="failed to publish message")
