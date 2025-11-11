from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.schemas import EmailRequest, StandardResponse
from app.config import settings
from app.utils.logger import get_logger
from app.services.email_sender import send_email_async
from app.services.email_service import send_email

logger = get_logger("main")
app = FastAPI(title="email_service", version="1.0")


@app.get("/health", response_model=StandardResponse)
def health():
    return JSONResponse({
        "success": True,
        "message": "email service healthy",
        "data": {},
        "meta": {}
    })


@app.post("/send_email", response_model=StandardResponse)
async def send_email_endpoint(payload: EmailRequest):
    """
    Send email using either real Gmail SMTP or fallback service.
    """
    if settings.use_real_smtp:
        success, error = await send_email_async(
            to_email=payload.to_email,
            subject=payload.subject or "No Subject",
            body=payload.body or ""
        )
    else:
        try:
            await send_email(
                recipient=payload.to_email,
                subject=payload.subject or "No Subject",
                body=payload.body or ""
            )
            success, error = True, None
        except Exception as e:
            success, error = False, str(e)

    if success:
        return {
            "success": True,
            "data": {"request_id": payload.request_id},
            "message": "Email sent successfully",
            "meta": {}
        }
    else:
        return {
            "success": False,
            "error": error,
            "message": "Failed to send email",
            "data": {},
            "meta": {}
        }
