from pydantic import BaseModel, EmailStr, validator
from typing import Dict, List, Optional, Any
from datetime import datetime

class EmailRequest(BaseModel):
    recipient_email: EmailStr
    subject: str
    body: str
    body_type: str = "html"
    priority: int = 1
    correlation_id: Optional[str] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in range(1, 6):
            raise ValueError('Priority must be between 1 and 5')
        return v
    
    @validator('body_type')
    def validate_body_type(cls, v):
        if v not in ['html', 'plain']:
            raise ValueError('Body type must be html or plain')
        return v

class EmailResponse(BaseModel):
    success: bool
    message: str
    correlation_id: Optional[str] = None
    data: Optional[dict] = None
    error: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    database: bool
    redis: bool
    rabbitmq: bool
    smtp: bool
    timestamp: datetime