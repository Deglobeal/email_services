# test_app.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.asyncio
async def test_send_email_success():
    payload = {
        "to_email": "test@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "abc123"
    }

    # Mock the async send_email_async function
    with patch("app.services.email_sender.send_email_async", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, None)  # simulate success
        response = client.post("/send_email", json=payload)
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is True
        assert data["data"]["request_id"] == payload["request_id"]
        mock_send.assert_awaited_once_with(
            to_email=payload["to_email"],
            subject=payload["subject"],
            body=payload["body"],
            html=False
        )

@pytest.mark.asyncio
async def test_send_email_failure():
    payload = {
        "to_email": "fail@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "xyz789"
    }

    with patch("app.services.email_sender.send_email_async", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = Exception("SMTP connection failed")
        response = client.post("/send_email", json=payload)
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is False
        assert "SMTP connection failed" in data["error"]
