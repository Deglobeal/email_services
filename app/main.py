from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
import uuid
import logging
from datetime import datetime

# Import database components correctly
from app.database import get_db, engine, Base, SessionLocal
from app.models import EmailQueue
from app.schemas import EmailRequest, EmailResponse, HealthCheck
from app.email_sender import EmailSender
from app.rabbitmq import rabbitmq_manager
from app.config import settings

logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Initialize email sender
email_sender = EmailSender(
    smtp_server=settings.smtp_server,
    smtp_port=settings.smtp_port,
    username=settings.smtp_username,
    password=settings.smtp_password
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # Test SMTP connection
    smtp_ok = email_sender.test_connection()
    if smtp_ok:
        logger.info("SMTP connection established")
    else:
        logger.warning("SMTP connection failed")

@app.get("/")
async def root():
    return {"message": "Email Service API", "status": "running"}

@app.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    # Check database
    db_healthy = False
    try:
        db.execute("SELECT 1") # type: ignore 
        db_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis (simplified)
    redis_healthy = True
    
    # Check RabbitMQ
    rabbitmq_healthy = False
    try:
        await rabbitmq_manager.connect()
        rabbitmq_healthy = True
    except Exception as e:
        logger.error(f"RabbitMQ health check failed: {e}")
    
    # Check SMTP
    smtp_healthy = email_sender.test_connection()
    
    overall_status = "healthy" if all([db_healthy, redis_healthy, rabbitmq_healthy, smtp_healthy]) else "unhealthy"
    
    return HealthCheck(
        status=overall_status,
        database=db_healthy,
        redis=redis_healthy,
        rabbitmq=rabbitmq_healthy,
        smtp=smtp_healthy,
        timestamp=datetime.now()
    )

@app.post("/send-email", response_model=EmailResponse)
async def send_email(
    email_request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send email immediately"""
    try:
        # Generate correlation ID if not provided
        correlation_id = email_request.correlation_id or str(uuid.uuid4())
        
        # Send email
        success = email_sender.send_email(
            recipient=email_request.recipient_email,
            subject=email_request.subject,
            body=email_request.body,
            body_type=email_request.body_type
        )
        
        if success:
            # Log successful send
            queue_item = EmailQueue(
                recipient_email=email_request.recipient_email,
                subject=email_request.subject,
                body=email_request.body,
                body_type=email_request.body_type,
                priority=email_request.priority,
                correlation_id=correlation_id,
                status="sent",
                processed_at=datetime.now()
            )
            db.add(queue_item)
            db.commit()
            
            return EmailResponse(
                success=True,
                message="Email sent successfully",
                correlation_id=correlation_id,
                data={
                    "recipient": email_request.recipient_email,
                    "status": "sent"
                }
            )
        else:
            return EmailResponse(
                success=False,
                message="Failed to send email - service unavailable",
                correlation_id=correlation_id,
                error="Email service unavailable due to circuit breaker"
            )
            
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
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
            recipient_email=email_request.recipient_email,
            subject=email_request.subject,
            body=email_request.body,
            body_type=email_request.body_type,
            priority=email_request.priority,
            correlation_id=correlation_id,
            status="pending"
        )
        
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        
        # Publish to RabbitMQ
        message = {
            "queue_item_id": queue_item.id,
            "recipient_email": email_request.recipient_email,
            "subject": email_request.subject,
            "body": email_request.body,
            "body_type": email_request.body_type,
            "correlation_id": correlation_id,
            "priority": email_request.priority
        }
        
        await rabbitmq_manager.publish_email_message(message)
        
        return EmailResponse(
            success=True,
            message="Email queued for processing",
            correlation_id=correlation_id,
            data={"queue_item_id": queue_item.id}
        )
        
    except Exception as e:
        logger.error(f"Failed to queue email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue email"
        )

@app.get("/status/{correlation_id}")
async def get_email_status(correlation_id: str, db: Session = Depends(get_db)):
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
            "subject": queue_item.subject,
            "processed_at": queue_item.processed_at,
            "error_message": queue_item.error_message,
            "retry_count": queue_item.retry_count
        },
        "message": f"Email status: {queue_item.status}"
    }

@app.get("/queue/stats")
async def get_queue_stats(db: Session = Depends(get_db)):
    """Get email queue statistics"""
    stats = {
        "pending": db.query(EmailQueue).filter(EmailQueue.status == "pending").count(),
        "processing": db.query(EmailQueue).filter(EmailQueue.status == "processing").count(),
        "sent": db.query(EmailQueue).filter(EmailQueue.status == "sent").count(),
        "failed": db.query(EmailQueue).filter(EmailQueue.status == "failed").count(),
        "total": db.query(EmailQueue).count()
    }
    
    return {
        "success": True,
        "data": stats,
        "message": "Queue statistics retrieved"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)