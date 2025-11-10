from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    subject = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    variables = Column(JSON)  # Expected variables for template
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EmailQueue(Base):
    __tablename__ = "email_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    variables = Column(JSON)  # Template variables
    status = Column(String(50), default="pending")  # pending, processing, sent, failed
    priority = Column(Integer, default=1)  # 1-5, 1 being highest
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text)
    correlation_id = Column(String(255), unique=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())