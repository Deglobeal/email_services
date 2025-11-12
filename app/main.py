from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
import asyncio
import signal
from app.services.queue_publisher import publish_email
from app.services.queue_consumer import consume
from app.utils.logger import get_logger

logger = get_logger("email_service_app")
app = FastAPI(title="Email Service", version="1.0.0")

email_status_store = {}

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    request_id: str | None = None
    priority: int | None = 1

class StatusRequest(BaseModel):
    request_id: str

@app.get("/")
async def root():
    """Root endpoint showing available endpoints"""
    return {
        "service": "Email Service",
        "status": "running",
        "docs": "/docs",
        "endpoints": ["/health", "/send_email", "/status", "/retry_failed"]
    }

@app.get("/health")
async def health_check():
    """Service health check endpoint"""
    return {"status": "ok", "service": "email_service"}

@app.post("/send_email")
async def send_email_endpoint(payload: EmailRequest):
    """Publish email message to RabbitMQ queue"""
    try:
        await publish_email(payload.to, payload.subject, payload.body)
        email_status_store[payload.request_id or payload.to] = "pending"
        return {"success": True, "message": "Email queued for delivery"}
    except Exception as e:
        logger.error({"status": "publish_failed", "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")

@app.post("/status")
async def status_endpoint(payload: StatusRequest):
    """Get delivery status of a specific request_id"""
    status = email_status_store.get(payload.request_id)
    if not status:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return {"request_id": payload.request_id, "status": status}

@app.post("/retry_failed")
async def retry_failed_endpoint():
    """Handle retrying of failed email deliveries"""
    return {"success": True, "message": "Retry initiated for failed emails"}

consumer_task: asyncio.Task | None = None

async def start_consumer():
    global consumer_task
    loop = asyncio.get_running_loop()

    def shutdown():
        if consumer_task:
            consumer_task.cancel()
        logger.info("Shutdown signal received. Stopping consumer...")

    loop.add_signal_handler(signal.SIGTERM, shutdown)
    loop.add_signal_handler(signal.SIGINT, shutdown)

    while True:
        try:
            consumer_task = asyncio.create_task(consume())
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")
            break
        except Exception as e:
            logger.error({"status": "consumer_crashed", "error": str(e)})
            logger.info("Restarting consumer in 5 seconds...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Start the RabbitMQ consumer in background on service startup"""
    asyncio.create_task(start_consumer())
