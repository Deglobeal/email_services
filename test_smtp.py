import smtplib
from email.mime.text import MIMEText
from app.config import settings

def send_test_email():
    msg = MIMEText("✅ This is a test email from your Stage 4 Email Service.")
    msg["Subject"] = "Test Email"
    msg["From"] = settings.email_from
    msg["To"] = settings.smtp_user

    try:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
            server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
            print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

if __name__ == "__main__":
    send_test_email()
