from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any

class EmailRequest(BaseModel):
    request_id: str = Field(..., description="unique idempotency key")
    to_email: EmailStr
    subject: Optional[str] = None
    body: Optional[str] = None
    meta: Optional[Dict[str, Any]] = {}

class StandardResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    message: str
    meta: Optional[Dict[str, Any]] = {}
