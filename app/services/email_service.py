from app.services.email_sender import send_email_async
from app.utils.logger import get_logger

logger = get_logger("email_service")

async def send_email(recipient: str, subject: str, body: str):
    success, error = await send_email_async(to_email=recipient, subject=subject, body=body)
    if not success:
        logger.error("email_send_failed", extra={"recipient": recipient, "subject": subject, "error": error})
        raise Exception(error)
    logger.info("email_send_success", extra={"recipient": recipient, "subject": subject})
