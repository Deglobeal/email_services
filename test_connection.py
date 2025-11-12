import smtplib, ssl

try:
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls(context=ssl.create_default_context())
        server.noop()
        print("✅ Connection to Gmail SMTP successful!")
except Exception as e:
    print("❌ Connection failed:", e)
