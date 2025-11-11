# tests/test_email_service_integration.py
import asyncio
import json
import pytest
from httpx import AsyncClient
from app.main import app
from app.config import settings

BASE_URL = "http://test"


@pytest.mark.anyio
async def test_health_endpoint():
    """Test /health endpoint returns standard response format and success=True"""
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "data" in body and "message" in body and "meta" in body


@pytest.mark.anyio
async def test_send_email_success(monkeypatch):
    """When mailer succeeds, endpoint must return success=True with request_id"""

    async def fake_send_email_async(to_email, subject, body, html=False):
        await asyncio.sleep(0)
        return True, None

    monkeypatch.setattr("app.services.email_sender.send_email_async", fake_send_email_async)

    payload = {
        "to_email": "valid@example.com",
        "subject": "Hello",
        "body": "This is a test",
        "request_id": "req-success-1"
    }

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.post("/send_email", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"].get("request_id") == payload["request_id"]
    assert "message" in body and body["message"]


@pytest.mark.anyio
async def test_send_email_failure_returns_error(monkeypatch):
    """When mailer fails, endpoint must return success=False with error"""

    async def fake_send_email_async_fail(to_email, subject, body, html=False):
        await asyncio.sleep(0)
        return False, "SMTP connection failed (simulated)"

    monkeypatch.setattr("app.services.email_sender.send_email_async", fake_send_email_async_fail)

    payload = {
        "to_email": "user@example.com",
        "subject": "Hello Fail",
        "body": "This will fail",
        "request_id": "req-fail-1"
    }

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.post("/send_email", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "SMTP connection failed" in (body.get("error") or "")


@pytest.mark.anyio
async def test_send_email_invalid_email_validation():
    """Invalid email format should be blocked or return success=False"""

    payload = {
        "to_email": "bad@@example..com",
        "subject": "Invalid",
        "body": "invalid email test",
        "request_id": "req-invalid-1"
    }

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.post("/send_email", json=payload)

    # either FastAPI/Pydantic returns 422 OR our endpoint returns success=False
    if resp.status_code == 422:
        assert "detail" in resp.json()
    else:
        body = resp.json()
        assert body["success"] is False


@pytest.mark.anyio
async def test_publish_email_calls_rabbitmq(monkeypatch):
    """Ensure /publish_email publishes to exchange 'notifications.direct' with routing_key 'email'"""

    published = {"called": False, "routing_key": None, "body": None}

    class DummyMessage:
        def __init__(self, body, delivery_mode=None):
            self.body = body

    class DummyExchange:
        async def publish(self, message, routing_key):
            published["called"] = True
            published["routing_key"] = routing_key
            try:
                published["body"] = json.loads(message.body.decode())
            except Exception:
                published["body"] = message.body

    class DummyChannel:
        async def declare_exchange(self, name, type=None, durable=False):
            assert name == "notifications.direct"
            return DummyExchange()

        async def close(self):
            pass

    class DummyConnection:
        async def channel(self):
            return DummyChannel()

        async def close(self):
            pass

    async def fake_connect_robust(url):
        assert url == settings.rabbitmq_url
        return DummyConnection()

    monkeypatch.setattr("aio_pika.connect_robust", fake_connect_robust)

    payload = {
        "to_email": "pub@example.com",
        "subject": "Publish Test",
        "body": "queue message",
        "request_id": "req-pub-1"
    }

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.post("/publish_email", json=payload)

    assert resp.status_code == 200
    assert published["called"] is True
    assert published["routing_key"] == "email"
    assert isinstance(published["body"], dict)
    assert published["body"]["request_id"] == payload["request_id"]


@pytest.mark.anyio
async def test_retry_logic_on_exception(monkeypatch):
    """Simulate send_email_async raising exceptions to ensure endpoint returns success=False"""

    call = {"attempts": 0}

    async def always_raise(to_email, subject, body, html=False):
        call["attempts"] += 1
        raise Exception("Simulated network failure")

    monkeypatch.setattr("app.services.email_sender.send_email_async", always_raise)

    payload = {
        "to_email": "retry@example.com",
        "subject": "Retry",
        "body": "retry test",
        "request_id": "req-retry-1"
    }

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:  # type: ignore[arg-type]
        resp = await ac.post("/send_email", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Simulated network failure" in (body.get("error") or "")
    assert call["attempts"] >= 1
