import asyncio
from aiosmtplib import SMTP, SMTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Update these with your settings
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # Works on your machine
SMTP_USER = "ugwugerard20@gmail.com"
SMTP_PASS = "geoifdisgbmbaxvo"
EMAIL_FROM = "ugwugerard20@gmail.com"
TO_EMAIL = "kachimaxy2@gmail.com"  # Replace with your test email

async def test_smtp():
    print(f"Testing Gmail SMTP connection to {SMTP_HOST}:{SMTP_PORT}...")
    msg = MIMEMultipart()
    msg["From"] = EMAIL_FROM
    msg["To"] = TO_EMAIL
    msg["Subject"] = "Local SMTP Test"
    msg.attach(MIMEText("Hello! This is a test email from local script.", "plain"))

    try:
        smtp = SMTP(hostname=SMTP_HOST, port=SMTP_PORT, use_tls=True, timeout=10)
        await smtp.connect()
        print("Connection successful!")
        await smtp.login(SMTP_USER, SMTP_PASS)
        print("Login successful!")
        await smtp.send_message(msg)
        print("Email sent successfully!")
        await smtp.quit()
    except SMTPException as e:
        print("SMTP Exception:", e)
    except Exception as e:
        print("General Exception:", e)

if __name__ == "__main__":
    asyncio.run(test_smtp())
