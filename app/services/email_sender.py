# email_sender.py
import asyncio
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("email_sender")

async def send_email_async(
    to_email: str,
    subject: str,
    body: str,
    html: bool = False
) -> tuple[bool, str | None]:
    """
    Send email via Gmail SMTP over SSL asynchronously.
    Supports retries using settings.max_retry_attempts
    """
    if not to_email or not subject or not body:
        raise ValueError("Recipient, subject, and body must be provided")

    # Prepare message
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg["Subject"] = subject

    mime_type = "html" if html else "plain"
    msg.attach(MIMEText(body, mime_type))

    attempt = 0
    while attempt < settings.max_retry_attempts:
        try:
            smtp = SMTP(
                hostname=settings.smtp_host,
                port=settings.smtp_port,  # 465 for SSL
                use_tls=True,  # SSL
                timeout=10
            )
            await smtp.connect()
            if settings.smtp_user:
                await smtp.login(settings.smtp_user, settings.smtp_pass)
            await smtp.send_message(msg)
            await smtp.quit()
            logger.info("email_sent", extra={"to_email": to_email, "subject": subject})
            return True, None

        except SMTPException as exc:
            attempt += 1
            logger.error(
                "smtp_error",
                extra={"attempt": attempt, "to_email": to_email, "error": str(exc)}
            )
            await asyncio.sleep(2 ** attempt)  # exponential backoff

        except Exception as exc:
            attempt += 1
            logger.error(
                "smtp_error_general",
                extra={"attempt": attempt, "to_email": to_email, "error": str(exc)}
            )
            await asyncio.sleep(2 ** attempt)

    return False, f"Failed to send email after {settings.max_retry_attempts} attempts"
