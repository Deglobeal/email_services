# test_gmail_smtp.py
import asyncio
from aiosmtplib import SMTP, SMTPException
from app.config import settings

async def test_smtp():
    print(f"Testing Gmail SMTP connection to {settings.smtp_host}:{settings.smtp_port}...")

    try:
        # STARTTLS (587) or SSL (465)
        use_ssl = settings.smtp_port == 465

        smtp = SMTP(
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=not use_ssl,  # True for 587, False for 465 SSL
            timeout=10,
            use_tls=use_ssl
        )
        await smtp.connect()
        print("Connection successful!")

        if settings.smtp_user:
            await smtp.login(settings.smtp_user, settings.smtp_pass)
            print("Login successful!")

        await smtp.quit()
        print("SMTP test completed successfully.")

    except SMTPException as e:
        print("SMTP Exception:", e)
    except Exception as e:
        print("General Exception:", e)

if __name__ == "__main__":
    asyncio.run(test_smtp())
