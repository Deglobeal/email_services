from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, cast
import uuid
import logging
from datetime import datetime
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
    # Check database
    db_healthy = False
    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
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
    
@app.get("/templates/{template_name}", response_model=EmailTemplateResponse)
def get_template(template_name: str, db: Session = Depends(get_db)):
    """Get template by name"""
    template = db.query(EmailTemplate).filter(
        EmailTemplate.name == template_name,
        EmailTemplate.is_active == True
    ).first()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found"
        )
    
    return template

@app.post("/send-email", response_model=EmailResponse)
async def send_email(
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send email immediately or queue for processing"""
    try:
        # Generate correlation ID if not provided
        correlation_id = email_request.correlation_id or str(uuid.uuid4())
        
        # Get template
        template = db.query(EmailTemplate).filter(
            EmailTemplate.name == email_request.template_name,
            EmailTemplate.is_active == True
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{email_request.template_name}' not found"
            )
        
        # Render template
        rendered_subject, rendered_body = template_engine.render_email(
            cast(str, template.subject),
            cast(str, template.body_template),
            email_request.variables
        )
        
        # Send email
        success = email_sender.send_email(
            recipient=email_request.recipient_email,
            subject=rendered_subject,
            body=rendered_body
        )
        
        if success:
            return EmailResponse(
                success=True,
                message="Email sent successfully",
                correlation_id=correlation_id,
                data={"recipient": email_request.recipient_email}
            )
        else:
            return EmailResponse(
                success=False,
                message="Failed to send email",
                correlation_id=correlation_id,
                error="Email service unavailable"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@app.post("/queue-email", response_model=EmailResponse)
async def queue_email(
    email_request: EmailRequest,
    db: Session = Depends(get_db)
):
    """Queue email for async processing"""
    try:
        correlation_id = email_request.correlation_id or str(uuid.uuid4())
        
        # Create queue entry
        queue_item = EmailQueue(
            template_name=email_request.template_name,
            recipient_email=email_request.recipient_email,
            variables=email_request.variables,
            priority=email_request.priority,
            correlation_id=correlation_id,
            status="pending"
        )
        
        db.add(queue_item)
        db.commit()
        
        # Publish to RabbitMQ
        message = {
            "queue_item_id": queue_item.id,
            "template_name": email_request.template_name,
            "recipient_email": email_request.recipient_email,
            "variables": email_request.variables,
            "correlation_id": correlation_id,
            "priority": email_request.priority
        }
        
        await rabbitmq_manager.publish_email_message(message)
        
        return EmailResponse(
            success=True,
            message="Email queued for processing",
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(f"Failed to queue email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue email"
        )

@app.get("/status/{correlation_id}")
def get_email_status(correlation_id: str, db: Session = Depends(get_db)):
    """Get email delivery status"""
    queue_item = db.query(EmailQueue).filter(
        EmailQueue.correlation_id == correlation_id
    ).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )
    
    return {
        "success": True,
        "data": {
            "status": queue_item.status,
            "recipient": queue_item.recipient_email,
            "template": queue_item.template_name,
            "processed_at": queue_item.processed_at,
            "error_message": queue_item.error_message,
            "retry_count": queue_item.retry_count
        },
        "message": f"Email status: {queue_item.status}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)