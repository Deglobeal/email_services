import smtplib

smtp_host = "smtp.gmail.com"
smtp_port = 465

try:
    server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
    server.quit()
    print("✅ Connection successful")
except Exception as e:
    print(f"❌ Connection failed: {e}")
