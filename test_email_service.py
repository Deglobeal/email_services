# test_email_service_endpoints.py

import asyncio
import json
import requests
from app.config import settings
from app.services.email_sender import send_email_async
import aio_pika
import time

BASE_URL = "http://127.0.0.1:8000"

# -----------------------------
# Async test for SMTP email directly
# -----------------------------
async def test_send_email():
    to_email = "kachimaxy2@gmail.com"  # Replace with your real test email
    subject = "Stage 4 Email Service SMTP Test"
    body = "Hello! This is a direct SMTP test email."

    success, error = await send_email_async(to_email, subject, body)
    if success:
        print("✅ SMTP Email sent successfully!")
    else:
        print(f"❌ Failed to send SMTP email: {error}")


# -----------------------------
# Test RabbitMQ connection
# -----------------------------
async def test_rabbitmq():
    try:
        connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        async with connection:
            print("✅ Connected to RabbitMQ")
    except Exception as e:
        print(f"❌ RabbitMQ connection failed: {e}")


# -----------------------------
# Test FastAPI endpoints
# -----------------------------
def test_api_endpoints():
    # Health check
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print("Health Check:", resp.json())
    except Exception as e:
        print("❌ Health check failed:", e)

    # Send email endpoint
    payload = {
        "to": "kachimaxy2@gmail.com",
        "subject": "Stage 4 /send_email Test",
        "body": "Hello from /send_email endpoint test!",
        "request_id": "test123"
    }

    try:
        resp = requests.post(f"{BASE_URL}/send_email/", json=payload)
        print("/send_email response:", resp.json())
    except Exception as e:
        print("❌ /send_email failed:", e)

    # Status endpoint
    payload_status = {"request_id": "test123"}
    try:
        resp = requests.post(f"{BASE_URL}/status/", json=payload_status)
        print("/status response:", resp.json())
    except Exception as e:
        print("❌ /status failed:", e)


# -----------------------------
# Run all tests
# -----------------------------
if __name__ == "__main__":
    print("=== Testing SMTP Email ===")
    asyncio.run(test_send_email())

    print("\n=== Testing RabbitMQ Connection ===")
    asyncio.run(test_rabbitmq())

    # Wait a bit for the consumer to process queued messages
    print("\n[Waiting 5 seconds for queue processing...]")
    time.sleep(5)

    print("\n=== Testing FastAPI Endpoints ===")
    test_api_endpoints()
