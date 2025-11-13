from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
import asyncio
import signal
import platform
import os
import logging
from logging.handlers import RotatingFileHandler

from app.services.queue_publisher import publish_email
from app.services.queue_consumer import consume
from app.utils.logger import get_logger


# Logging setup (writes to console + rotating file)

os.makedirs("logs", exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log_file = "logs/email_service.log"

file_handler = RotatingFileHandler(log_file, maxBytes=10_000_000, backupCount=5)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("email_service_app")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
# ==========================================================


app = FastAPI(title="Email Service", version="1.0.0")

email_status_store = {}


# Models

class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    request_id: str | None = None
    priority: int | None = 1


class StatusRequest(BaseModel):
    request_id: str


# Middleware for request logging

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        f"Incoming request: {request.method} {request.url} from {request.client.host if request.client else 'unknown'}"
    )
    try:
        response = await call_next(request)
        logger.info(f"Request completed: {request.method} {request.url} → {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url} | Error: {str(e)}")
        raise


# Routes

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "service": "Email Service",
        "status": "running",
        "docs": "/docs",
        "endpoints": ["/health", "/send_email", "/status", "/retry_failed"],
    }


@app.get("/health")
async def health_check():
    logger.info("Health check OK")
    return {"status": "ok", "service": "email_service"}


@app.post("/send_email")
async def send_email_endpoint(payload: EmailRequest):
    logger.info(f"Email send request: to={payload.to}, subject={payload.subject}, id={payload.request_id}")

    try:
        await publish_email(payload.to, payload.subject, payload.body)
        key = payload.request_id or payload.to
        email_status_store[key] = "pending"

        logger.info(f"Email queued successfully: {payload.to} | request_id={key}")
        return {"success": True, "message": "Email queued for delivery"}

    except Exception as e:
        logger.error(f"Failed to queue email: {str(e)} for {payload.to}")
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")


@app.post("/status")
async def status_endpoint(payload: StatusRequest):
    logger.info(f"Status check for request_id={payload.request_id}")
    status = email_status_store.get(payload.request_id)

    if not status:
        logger.warning(f"Status not found for {payload.request_id}")
        raise HTTPException(status_code=404, detail="Request ID not found")

    logger.info(f"Status fetched: {payload.request_id} → {status}")
    return {"request_id": payload.request_id, "status": status}


@app.post("/retry_failed")
async def retry_failed_endpoint():
    logger.info("Retry failed emails triggered")
    # TODO: Add retry mechanism
    return {"success": True, "message": "Retry initiated for failed emails"}


# Background Consumer Task

consumer_task: asyncio.Task | None = None

async def start_consumer():
    """Run RabbitMQ consumer loop safely"""
    global consumer_task
    loop = asyncio.get_running_loop()

    def shutdown():
        if consumer_task:
            consumer_task.cancel()
        logger.info("Shutdown signal received — stopping consumer...")

    # Handle signal setup based on OS
    if platform.system() != "Windows":
        try:
            loop.add_signal_handler(signal.SIGTERM, shutdown)
            loop.add_signal_handler(signal.SIGINT, shutdown)
        except NotImplementedError:
            logger.warning("Signal handlers not implemented on this platform.")
    else:
        logger.warning("Windows detected — skipping signal handler setup.")

    while True:
        try:
            consumer_task = asyncio.create_task(consume())
            logger.info("Consumer started successfully.")
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled — shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Consumer crashed: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    """Start the RabbitMQ consumer on service startup"""
    logger.info("Service startup — launching consumer background task.")
    asyncio.create_task(start_consumer())
