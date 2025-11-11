from app.config import settings  
from app.services.email_service import send_email
from app.utils.logger import get_logger
from email.mime.text import MIMEText
from smtplib import SMTPException
from aiosmtplib import SMTP
from email.mime.multipart import MIMEMultipart 
import smtplib

logger = get_logger(__name__)


async def send_email(recipient: str, subject: str, body: str):
    """
    Send email using SMTP with settings from config.py
    """
    if recipient is None or subject is None or body is None:
        raise ValueError("Recipient, subject, and body must be provided")

    msg = MIMEMultipart()
    msg["From"] = settings.email_from
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
        logger.info("email_sent", extra={"to": recipient, "subject": subject})
    except SMTPException as e:
        logger.error(
            "email_failed",
            extra={"to": recipient, "error": str(e)}
        )
        raise e