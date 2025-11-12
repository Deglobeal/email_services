import asyncio
import re
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.utils.logger import get_logger
from app.services.circuit_breaker import CircuitBreaker

logger = get_logger("email_sender")
EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
circuit = CircuitBreaker(failure_threshold=3, recovery_time=20)  # 3 failures open circuit for 20 sec

async def send_email_async(to_email: str, subject: str, body: str, html: bool = False):
    """
    Sends an email asynchronously via Gmail SMTP (STARTTLS recommended on port 587)
    Implements retries with exponential backoff and circuit breaker protection.
    """
    if not circuit.allow_request():
        logger.warning("circuit_open", extra={"to_email": to_email})
        return False, "Circuit breaker is OPEN"

    if not to_email or not subject or not body:
        return False, "Recipient, subject, and body must be provided"

    if not EMAIL_REGEX.match(to_email):
        logger.warning("invalid_email_format", extra={"to_email": to_email})
        return False, "Invalid email address format"

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if html else "plain"))

    for attempt in range(1, settings.max_retry_attempts + 1):
        try:
            # Gmail STARTTLS configuration
            smtp = SMTP(
                hostname=settings.smtp_host,
                port=settings.smtp_port,  # Should be 587 for STARTTLS
                start_tls=True,
                timeout=10
            )
            await smtp.connect()
            if settings.smtp_user:
                await smtp.login(settings.smtp_user, settings.smtp_pass)
            await smtp.send_message(msg)
            await smtp.quit()

            circuit.record_success()
            logger.info("email_sent", extra={"to_email": to_email, "subject": subject, "attempt": attempt})
            return True, None

        except Exception as e:
            circuit.record_failure()
            logger.error(
                "smtp_error",
                extra={"attempt": attempt, "to_email": to_email, "error": str(e)}
            )
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    logger.error(
        "email_failed_after_retries",
        extra={"to_email": to_email, "attempts": settings.max_retry_attempts}
    )
    return False, f"Failed after {settings.max_retry_attempts} attempts"
