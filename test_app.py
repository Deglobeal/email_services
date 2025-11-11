import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

@pytest.mark.asyncio
async def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_send_email_success():
    payload = {
        "to_email": "test@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "abc123"
    }

    if settings.use_real_smtp:
        response = client.post("/send_email", json=payload)
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is True
    else:
        # Mock version
        with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = None
            response = client.post("/send_email", json=payload)
            data = response.json()
            assert response.status_code == 200
            assert data["success"] is True

@pytest.mark.asyncio
async def test_send_email_failure():
    payload = {
        "to_email": "fail@example.com",
        "subject": "Test Email",
        "body": "Hello World",
        "request_id": "xyz789"
    }

    if settings.use_real_smtp:
        # For real SMTP, just test with invalid email to force failure
        response = client.post("/send_email", json=payload)
        data = response.json()
        assert response.status_code == 200
        assert data["success"] is False
    else:
        # Mock version
        with patch("app.services.email_service.send_email", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = Exception("SMTP connection failed")
            response = client.post("/send_email", json=payload)
            data = response.json()
            assert response.status_code == 200
            assert data["success"] is False
            assert "SMTP connection failed" in data["error"]
