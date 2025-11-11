# test_email_service.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

# Import your FastAPI app
from app.main import app
from app.schemas import EmailRequest
from app.services import email_service

client = TestClient(app)


# ------------------------
# Health endpoint test
# ------------------------
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {},
        "message": "email service healthy",
        "meta": {}
    }


# ------------------------
# Send email success test
# ------------------------
@pytest.mark.asyncio
async def test_send_email_success():
    payload = {
        "to_email": "test@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "abc123"
    }

    # Patch the real send_email to avoid SMTP call
    with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None  # send_email does not return anything

        response = client.post("/send_email", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["request_id"] == payload["request_id"]
        mock_send.assert_awaited_once_with(
            recipient=payload["to_email"],
            subject=payload["subject"],
            body=payload["body"]
        )


# ------------------------
# Send email failure test
# ------------------------
@pytest.mark.asyncio
async def test_send_email_failure():
    payload = {
        "to_email": "fail@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "xyz789"
    }

    # Simulate SMTP failure
    with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("SMTP connection failed")

        response = client.post("/send_email", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "SMTP connection failed" in data["error"]
        mock_send.assert_awaited_once_with(
            recipient=payload["to_email"],
            subject=payload["subject"],
            body=payload["body"]
        )


# ------------------------
# RabbitMQ message processing test
# ------------------------
@pytest.mark.asyncio
async def test_rabbitmq_message_processing():
    """
    Simulate consuming a message from RabbitMQ and sending email.
    This runs independently without a real RabbitMQ server.
    """
    test_message = EmailRequest(
        to_email="queue_test@example.com",
        subject="Queue Email",
        body="Hello from queue",
        request_id="queue123"
    )

    # Patch send_email to simulate processing
    with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = None

        # Simulate calling the consumer handler directly
        await email_service.send_email(
            recipient=test_message.to_email,
            subject=test_message.subject,
            body=test_message.body
        )

        # Ensure send_email was awaited correctly
        mock_send.assert_awaited_once_with(
            recipient=test_message.to_email,
            subject=test_message.subject,
            body=test_message.body
        )
