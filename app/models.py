# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

class EmailStatusEnum(str, enum.Enum):
    queued = "queued"
    sending = "sending"
    sent = "sent"
    failed = "failed"

class EmailStatus(Base):
    __tablename__ = "email_status"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(128), unique=True, nullable=False, index=True)
    to_email = Column(String(254), nullable=False, index=True)
    subject = Column(String(512), nullable=True)
    body = Column(Text, nullable=True)
    status = Column(Enum(EmailStatusEnum), default=EmailStatusEnum.queued, nullable=False)
    attempt = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    meta = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
