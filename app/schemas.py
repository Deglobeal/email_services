from pydantic import BaseModel, EmailStr, validator
from typing import Dict, List, Optional, Any
from datetime import datetime

class EmailTemplateCreate(BaseModel):
    name: str
    subject: str
    body_template: str
    language: str = "en"
    variables: Optional[Dict[str, Any]] = None

class EmailTemplateResponse(BaseModel):
    id: int
    name: str
    subject: str
    body_template: str
    language: str
    variables: Optional[Dict[str, Any]]
    is_active: bool
    version: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmailRequest(BaseModel):
    template_name: str
    recipient_email: EmailStr
    variables: Dict[str, Any]
    priority: int = 1
    correlation_id: Optional[str] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in range(1, 6):
            raise ValueError('Priority must be between 1 and 5')
        return v
    
class EmailResponse(BaseModel):
    success: bool
    message: str
    correlation_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class HealthCheck(BaseModel):
    status: str
    database: bool
    redis: bool
    rabbitmq: bool
    timestamp: datetime