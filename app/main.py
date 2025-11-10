from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Dict, Any
import uuid
import logging
from .database import get_db
from .models import EmailTemplate, EmailQueue
from .schemas import (
    EmailTemplateCreate, EmailTemplateResponse, 
    EmailRequest, EmailResponse, HealthCheck
)
from .template_engine import template_engine
from .email_sender import EmailSender
from .rabbitmq import rabbitmq_manager
from .config import settings

logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize email sender
email_sender = EmailSender(
    smtp_server=settings.smtp_server,
    smtp_port=settings.smtp_port,
    username=settings.smtp_username,
    password=settings.smtp_password
)

@app.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    # Check database
    db_healthy = False
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis (simplified - you'd use redis client in real implementation)
    redis_healthy = True
    
    # Check RabbitMQ
    rabbitmq_healthy = False
    try:
        await rabbitmq_manager.connect()
        rabbitmq_healthy = True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
    
    return HealthCheck(
        status="healthy" if all([db_healthy, redis_healthy, rabbitmq_healthy]) else "unhealthy",
        database=db_healthy,
        redis=redis_healthy,
        rabbitmq=rabbitmq_healthy,
        timestamp=datetime.now()
    )

@app.post("/templates", response_model=EmailTemplateResponse)
def create_template(
    template: EmailTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create new email template"""
    try:
        # Validate template syntax
        template_engine.validate_variables(template.body_template, {})
        
        db_template = EmailTemplate(**template.dict())
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        return db_template
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )