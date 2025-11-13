from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr
import asyncio
import signal
import platform
import os
import json
from fastapi.responses import HTMLResponse
import logging
from logging.handlers import RotatingFileHandler
from fastapi.staticfiles import StaticFiles
from app.services.queue_publisher import publish_email
from app.services.queue_consumer import consume
from app.utils.logger import get_logger
from app.services.email_sender import send_email_async
from app.config import settings

if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # UTF-8

app = FastAPI(title="Email Service", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static") 

# Logging setup (console + rotating file)
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

if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

email_status_store: dict[str, str] = {}

# Models
class EmailRequest(BaseModel):
    to: EmailStr
    subject: str
    body: str
    request_id: str | None = None
    priority: int | None = 1

class StatusRequest(BaseModel):
    request_id: str

# Middleware for logging
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
@app.get("/", response_class=HTMLResponse)
async def root():
    base_url = "https://emailservices-production.up.railway.app"
    html_content = f"""
    <html>
    <head><title>Email Service Home</title></head>
    <body>
        <h1>Email Service</h1>
        <p>Status: <strong>Running ✅</strong></p>
        <p>Version: 1.0.0</p>
        <ul>
            <li><a href="{base_url}/health" target="_blank">/health</a></li>
            <li><a href="{base_url}/send_email" target="_blank">/send_email</a></li>
            <li><a href="{base_url}/status" target="_blank">/status</a></li>
            <li><a href="{base_url}/retry_failed" target="_blank">/retry_failed</a></li>
            <li><a href="{base_url}/logs" target="_blank">/logs</a></li>
            <li><a href="{base_url}/tester" target="_blank">/tester</a></li>
            <li><a href="{base_url}/view_statuses" target="_blank">/view_statuses</a></li>
        </ul>
        <p>API Docs: <a href="{base_url}/docs" target="_blank">/docs</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    logger.info("Health check OK")
    return {"status": "ok", "service": "email_service"}

@app.post("/send_email")
async def send_email_endpoint(payload: EmailRequest):
    logger.info(f"Email send request: to={payload.to}, subject={payload.subject}, id={payload.request_id}")
    try:
        await publish_email(payload.to, payload.subject, payload.body)
        key = str(payload.request_id or payload.to)
        email_status_store[key] = "pending"
        logger.info(f"Email queued successfully: {payload.to} | request_id={key}")
        return {"success": True, "message": "Email queued for delivery"}
    except Exception as e:
        logger.error(f"Failed to queue email: {str(e)} for {payload.to}")
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")

@app.get("/test_smtp")
async def test_smtp():
    to_test_email = settings.smtp_user
    subject = "SMTP Test"
    body = "This is a test email from the deployed server."
    success, error = await send_email_async(to_test_email, subject, body)
    if success:
        return {"success": True, "message": "SMTP connection successful, email sent!"}
    return {"success": False, "error": error}

@app.post("/status")
async def status_endpoint(payload: StatusRequest):
    logger.info(f"Status check for request_id={payload.request_id}")
    status = email_status_store.get(payload.request_id)
    if not status:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return {"request_id": payload.request_id, "status": status}

@app.post("/retry_failed")
async def retry_failed_endpoint():
    logger.info("Retry failed emails triggered")
    # TODO: implement retry mechanism
    return {"success": True, "message": "Retry initiated for failed emails"}

# Background consumer
consumer_task: asyncio.Task | None = None

async def start_consumer():
    global consumer_task
    loop = asyncio.get_running_loop()

    if platform.system() != "Windows":
        def shutdown_signal_handler():
            if consumer_task:
                consumer_task.cancel()
        loop.add_signal_handler(signal.SIGTERM, shutdown_signal_handler)
        loop.add_signal_handler(signal.SIGINT, shutdown_signal_handler)

    while True:
        try:
            consumer_task = asyncio.create_task(consume())
            await consumer_task
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Consumer crashed: {e}. Restarting in 5 seconds...")
            await asyncio.sleep(5)

async def stop_consumer():
    global consumer_task
    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled successfully.")

@app.on_event("startup")
async def on_startup():
    logger.info("Service startup — launching consumer task.")
    asyncio.create_task(start_consumer())

@app.on_event("shutdown")
async def on_shutdown():
    await stop_consumer()
    logger.info("Application shutdown complete.")

# Logs viewer
@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    log_file_path = os.path.join("logs", "structured_logs.json")
    html_content = "<html><body><h1>Logs</h1><table><tr><th>Time</th><th>Level</th><th>Request ID</th><th>Message</th></tr>"
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    html_content += f"<tr class='{entry.get('levelname','')}'><td>{entry.get('asctime','')}</td><td>{entry.get('levelname','')}</td><td>{entry.get('request_id','')}</td><td>{entry.get('message','')}</td></tr>"
                except:
                    continue
    html_content += "</table></body></html>"
    return HTMLResponse(content=html_content)

@app.get("/tester", response_class=HTMLResponse)
async def tester():
    return HTMLResponse(open("app/static/test_api.html").read())

@app.get("/view_statuses", response_class=HTMLResponse)
async def view_statuses():
    html_content = "<html><body><h1>Email Statuses</h1><table><tr><th>Request ID</th><th>Status</th></tr>"
    for rid, status in email_status_store.items():
        html_content += f"<tr><td>{rid}</td><td>{status}</td></tr>"
    if not email_status_store:
        html_content += "<tr><td colspan='2'>No requests found.</td></tr>"
    html_content += "</table></body></html>"
    return HTMLResponse(content=html_content)

@app.get("/test-email")
async def test_email_queue():
    try:
        await publish_email(
            to="test@example.com",
            subject="Test Email Queue",
            body="This is a test email message from FastAPI endpoint.",
            request_id="fastapi-test-001",
        )
        return {"success": True, "message": "Test email queued successfully"}
    except Exception as e:
        logger.error(f"Failed to publish test email: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue email: {str(e)}")
