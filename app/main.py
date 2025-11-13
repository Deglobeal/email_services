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


if os.name == "nt":
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)  # UTF-8

app = FastAPI(title="Email Service", version="1.0.0")

app.mount("/static", StaticFiles(directory="app/static"), name="static") 

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

@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page showing service info and all endpoints with clickable links"""
    base_url = "https://emailservices-production.up.railway.app"

    html_content = f"""
    <html>
    <head>
        <title>Email Service Home</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            ul {{ line-height: 1.8; }}
            a {{ text-decoration: none; color: #007BFF; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <h1>Email Service</h1>
        <p>Status: <strong>Running ✅</strong></p>
        <p>Version: 1.0.0</p>
        <h2>Available Endpoints</h2>
        <ul>
            <li><a href="{base_url}/health" target="_blank">/health</a> - Service health check</li>
            <li><a href="{base_url}/send_email" target="_blank">/send_email</a> - Send an email (POST)</li>
            <li><a href="{base_url}/status" target="_blank">/status</a> - Check email status (POST)</li>
            <li><a href="{base_url}/retry_failed" target="_blank">/retry_failed</a> - Retry failed emails (POST)</li>
            <li><a href="{base_url}/logs" target="_blank">/logs</a> - View structured logs (HTML)</li>
            <li><a href="{base_url}/tester" target="_blank">/tester</a> - Test API page</li>
            <li><a href="{base_url}/view_statuses" target="_blank">/view_statuses</a> - View all email statuses (HTML)</li>
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

    # Windows doesn't support signal handlers in asyncio
    if platform.system() != "Windows":
        def shutdown_signal_handler():
            if consumer_task:
                consumer_task.cancel()
                logger.info("Shutdown signal received — stopping consumer...")
        try:
            loop.add_signal_handler(signal.SIGTERM, shutdown_signal_handler)
            loop.add_signal_handler(signal.SIGINT, shutdown_signal_handler)
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

# ----------------- STOP CONSUMER -----------------
async def stop_consumer():
    """Cancel consumer task gracefully"""
    global consumer_task
    if consumer_task and not consumer_task.done():
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled successfully.")

# ----------------- LIFECYCLE HOOKS -----------------
@app.on_event("startup")
async def on_startup():
    logger.info("Service startup — launching consumer background task.")
    asyncio.create_task(start_consumer())

@app.on_event("shutdown")
async def on_shutdown():
    await stop_consumer()
    logger.info("Application shutdown complete.")


# logs html endpoint



@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    """Render structured JSON logs as a color-coded HTML table"""
    log_file_path = os.path.join("logs", "structured_logs.json")
    
    html_content = """
    <html>
    <head>
        <title>Email Service Logs</title>
        <meta http-equiv="refresh" content="900"> <!-- auto-refresh every 15 minutes -->
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .INFO { background-color: #d4edda; }
            .WARNING { background-color: #fff3cd; }
            .ERROR { background-color: #f8d7da; }
            .DEBUG { background-color: #d1ecf1; }
            .CRITICAL { background-color: #f5c6cb; }
            button { margin-bottom: 10px; padding: 6px 12px; }
        </style>
    </head>
    <body>
        <h1>Email Service Logs</h1>
        <button onclick="window.location.reload()">Refresh Now</button>
        <table>
            <tr>
                <th>Time</th>
                <th>Level</th>
                <th>Request ID</th>
                <th>Message</th>
            </tr>
    """

    # Render log entries
    if os.path.exists(log_file_path):
        with open(log_file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    log_entry = json.loads(line)
                    level = log_entry.get("levelname", "")
                    html_content += f"""
                    <tr class="{level}">
                        <td>{log_entry.get('asctime','')}</td>
                        <td>{level}</td>
                        <td>{log_entry.get('request_id','')}</td>
                        <td>{log_entry.get('message','')}</td>
                    </tr>
                    """
                except json.JSONDecodeError:
                    continue
    else:
        html_content += "<tr><td colspan='4'>No logs found.</td></tr>"

    html_content += """
        </table>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)

@app.get("/tester", response_class=HTMLResponse)
async def tester():
    return HTMLResponse(open("app/static/test_api.html").read())



@app.get("/view_statuses", response_class=HTMLResponse)
async def view_statuses():
    """Render all request IDs and their statuses as an HTML table"""
    html_content = """
    <html>
    <head>
        <title>Email Request Statuses</title>
        <meta http-equiv="refresh" content="900"> <!-- Refresh every 15 minutes -->
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>Email Request Statuses</h1>
        <table>
            <tr>
                <th>Request ID</th>
                <th>Status</th>
            </tr>
    """

    # Populate table rows
    for request_id, status in email_status_store.items():
        html_content += f"""
            <tr>
                <td>{request_id}</td>
                <td>{status}</td>
            </tr>
        """

    if not email_status_store:
        html_content += "<tr><td colspan='2'>No requests found.</td></tr>"

    html_content += """
        </table>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


