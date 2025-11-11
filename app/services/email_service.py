from app.config import settings
from app.services.email_sender import send_email_async  # use email_sender
from app.utils.logger import get_logger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = get_logger(__name__)


async def send_email(recipient: str, subject: str, body: str):
    """Wrapper for async email sending using email_sender."""
    success, error = await send_email_async(
        to_email=recipient,
        subject=subject,
        body=body
    )
    if not success:
        raise Exception(error)