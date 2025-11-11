# tests/test_app.py
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app  # your FastAPI app
from app.models import User, EmailLog
from app.db import Base, engine, SessionLocal

# Use a test database
@pytest.fixture(scope="module")
def test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    return TestClient(app)

def test_home(client):
    response = client.get("/")
    assert response.status_code == 200

def test_create_user(test_db):
    db = SessionLocal()
    user = User(username="tester", email="tester@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    db.delete(user)
    db.commit()

def test_email_log(test_db):
    db = SessionLocal()
    log = EmailLog(to_email="test@example.com", subject="Hello", body="Body")
    db.add(log)
    db.commit()
    db.refresh(log)
    assert log.id is not None
    db.delete(log)
    db.commit()
