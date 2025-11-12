import asyncio
from app.services.email_sender import send_email_async

async def main():
    success, error = await send_email_async(
        to_email="kachimaxy2@gmail.com",  # use an alternate inbox
        subject="✅ Async Gmail Test",
        body="Hello! This is a test email sent via aiosmtplib and FastAPI."
    )
    if success:
        print("✅ Email sent successfully!")
    else:
        print(f"❌ Failed: {error}")

asyncio.run(main())
