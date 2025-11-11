# app/services/email_service.py

from app.services.email_sender import send_email_async
from app.utils.logger import get_logger

logger = get_logger("email_service")


async def send_email(recipient: str, subject: str, body: str) -> None:
    """
    Wrapper around send_email_async for higher-level use.
    Raises an exception if sending fails, so that upstream
    handlers (e.g., FastAPI endpoint) can catch it.
    """
    success, error = await send_email_async(
        to_email=recipient,
        subject=subject,
        body=body
    )

    if not success:
        logger.error(
            "email_send_failed",
            extra={"recipient": recipient, "subject": subject, "error": error},
        )
        raise Exception(error or "Unknown email sending error")

    logger.info(
        "email_send_success",
        extra={"recipient": recipient, "subject": subject},
    )
