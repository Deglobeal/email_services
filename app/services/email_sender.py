import asyncio
import re
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("email_sender")
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")

async def send_email_async(to_email: str, subject: str, body: str, html: bool = False) -> tuple[bool, str | None]:
    if not to_email or not subject or not body:
        return False, "Recipient, subject, and body must be provided"

    if not EMAIL_REGEX.match(to_email):
        logger.warning("invalid_email_format", extra={"to_email": to_email})
        return False, "Invalid email address format"

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject
    mime_type = "html" if html else "plain"
    msg.attach(MIMEText(body, mime_type))

    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            smtp = SMTP(hostname=settings.smtp_host, port=settings.smtp_port, use_tls=True, timeout=10)
            await smtp.connect()
            if settings.smtp_user:
                await smtp.login(settings.smtp_user, settings.smtp_pass)
            await smtp.send_message(msg)
            await smtp.quit()
            logger.info("email_sent", extra={"to_email": to_email, "subject": subject, "attempt": attempt})
            return True, None
        except (SMTPException, Exception) as exc:
            logger.error("smtp_error", extra={"attempt": attempt, "to_email": to_email, "error": str(exc)})
            if attempt < settings.max_retry_attempts:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error("email_failed_after_retries", extra={"to_email": to_email, "attempts": attempt, "error": str(exc)})
                return False, f"Failed after {attempt} attempts: {str(exc)}"

    return False, "Unexpected error: retry loop exited without success"
