import asyncio
import json
import logging
import time
from sqlalchemy.orm import Session
from aio_pika import IncomingMessage
from datetime import datetime

# Import database correctly
from app.database import SessionLocal
from app.models import EmailQueue
from app.email_sender import EmailSender
from app.rabbitmq import rabbitmq_manager
from app.config import settings

logger = logging.getLogger(__name__)

class EmailWorker:
    def __init__(self):
        self.email_sender = EmailSender(
            smtp_server=settings.smtp_server,
            smtp_port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password
        )
        self.max_retries = 3
        self.processing = False
    
    async def process_message(self, message: IncomingMessage):
        """Process individual email message from queue"""
        async with message.process():
            try:
                message_data = json.loads(message.body.decode())
                correlation_id = message_data.get('correlation_id', 'unknown')
                logger.info(f"Processing email message: {correlation_id}")
                
                # Update database status to processing
                db = SessionLocal()
                try:
                    queue_item = db.query(EmailQueue).filter(
                        EmailQueue.id == message_data['queue_item_id']
                    ).first()
                    
                    if not queue_item:
                        logger.error(f"Queue item not found: {message_data['queue_item_id']}")
                        await message.ack()
                        return
                    
                    # Mark as processing
                    queue_item.status = "processing"   # type: ignore
                    db.commit()
                    
                    # Send email
                    success = self.email_sender.send_email(
                        recipient=queue_item.recipient_email,   # type: ignore
                        subject=queue_item.subject,   # type: ignore
                        body=queue_item.body,   # type: ignore
                        body_type=queue_item.body_type   # type: ignore
                    )
                    
                    if success:
                        queue_item.status = "sent"   # type: ignore
                        queue_item.processed_at = datetime.now()   # type: ignore
                        logger.info(f"Email sent successfully: {correlation_id}")
                    else:
                        raise Exception("Email sending failed - circuit breaker open")
                    
                    db.commit()
                    await message.ack()
                    
                except Exception as e:
                    logger.error(f"Failed to process email {correlation_id}: {e}")
                    
                    # Handle retries
                    current_retry_count = message.headers.get('x-retry-count', 0) if message.headers else 0
                    
                    if current_retry_count >= self.max_retries:   # type: ignore
                        # Permanent failure - update status
                        queue_item.status = "failed"   # type: ignore
                        queue_item.error_message = str(e)   # type: ignore
                        queue_item.processed_at = datetime.now()   # type: ignore
                        db.commit()
                        
                        await rabbitmq_manager.move_to_failed_queue(message, str(e))
                        logger.error(f"Email permanently failed after {current_retry_count} retries: {correlation_id}")
                    else:
                        # Requeue with incremented retry count
                        queue_item.status = "pending"   # type: ignore
                        queue_item.retry_count = current_retry_count + 1   # type: ignore
                        queue_item.error_message = str(e)   # type: ignore
                        db.commit()
                        
                        # Requeue with delay
                        await self.requeue_message(message_data, current_retry_count + 1)   # type: ignore
                        await message.ack()
                        logger.warning(f"Email requeued for retry {current_retry_count + 1}: {correlation_id}")   # type: ignore
                    
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                # Nack the message without requeue
                await message.nack(requeue=False)
    
    async def requeue_message(self, message_data: dict, retry_count: int):
        """Requeue message with exponential backoff"""
        delay = min(300, (2 ** retry_count) * 30)  # Max 5 minutes delay, exponential backoff
        
        logger.info(f"Requeuing message {message_data['correlation_id']} with {delay}s delay (retry {retry_count})")
        
        await asyncio.sleep(delay)
        
        # Update message headers with new retry count
        message_data['retry_count'] = retry_count
        await rabbitmq_manager.publish_email_message(message_data)
    
    async def start_processing(self):
        """Start processing email queue messages"""
        if self.processing:
            return
        
        self.processing = True
        logger.info("Starting email worker")
        
        await rabbitmq_manager.connect()
        await rabbitmq_manager.consume_email_messages(self.process_message)
    
    async def stop_processing(self):
        """Stop processing messages"""
        self.processing = False
        logger.info("Stopping email worker")

# Create global worker instance
email_worker = EmailWorker()

async def main():
    """Main function to run the worker"""
    worker = EmailWorker()
    logger.info("Starting Email Service Worker...")
    
    try:
        await worker.start_processing()
        
        # Keep the worker running
        while worker.processing:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal...")
        await worker.stop_processing()
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        await worker.stop_processing()

if __name__ == "__main__":
    asyncio.run(main())