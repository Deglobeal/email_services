import asyncio
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("email_sender")

async def send_email_async(to_email: str, subject: str, body: str):
    message = MIMEText(body or "", "html")
    message["From"] = settings.email_from
    message["To"] = to_email
    message["Subject"] = subject or ""

    smtp = SMTP(hostname=settings.smtp_host, port=settings.smtp_port, start_tls=True)
    try:
        await smtp.connect()
        if settings.smtp_user:
            await smtp.login(settings.smtp_user, settings.smtp_pass)
        await smtp.send_message(message)
        await smtp.quit()
        logger.info("email_sent", extra={"to_email": to_email})
        return True, None
    except SMTPException as exc:
        logger.error("smtp_error", extra={"error": str(exc)})
        try:
            await smtp.quit()
        except Exception:
            pass
        return False, str(exc)
