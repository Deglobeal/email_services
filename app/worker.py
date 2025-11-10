import asyncio
import json
import logging
from sqlalchemy.orm import Session
from aio_pika import IncomingMessage

from .database import SessionLocal
from .models import EmailQueue, EmailTemplate
from .template_engine import template_engine
from .email_sender import email_sender
from .rabbitmq import rabbitmq_manager
from .config import settings

logger = logging.getLogger(__name__)


class EmailWorker:
    def __init__(self):
        self.max_retries = 3
        self.processing = False
    
    async def process_message(self, message: IncomingMessage):
        """Process individual email message from queue"""
        async with message.process():
            try:
                message_data = json.loads(message.body.decode())
                logger.info(f"Processing email message: {message_data.get('correlation_id')}")
                
                # Update database status
                db = SessionLocal()
                try:
                    queue_item = db.query(EmailQueue).filter(
                        EmailQueue.id == message_data['queue_item_id']
                    ).with_for_update().first()
                    
                    if not queue_item:
                        logger.error(f"Queue item not found: {message_data['queue_item_id']}")
                        await message.ack()
                        return
                    
                    # Mark as processing
                    queue_item.status = "processing"
                    db.commit()
                    
                    # Get template
                    template = db.query(EmailTemplate).filter(
                        EmailTemplate.name == queue_item.template_name,
                        EmailTemplate.is_active == True
                    ).first()
                    
                    if not template:
                        raise ValueError(f"Template '{queue_item.template_name}' not found")
                    
                    # Render email
                    rendered_subject, rendered_body = template_engine.render_email(
                        template.subject,
                        template.body_template,
                        queue_item.variables or {}
                    )
                    
                    # Send email
                    success = email_sender.send_email(
                        recipient=queue_item.recipient_email,
                        subject=rendered_subject,
                        body=rendered_body
                    )
                    
                    if success:
                        queue_item.status = "sent"
                        queue_item.processed_at = func.now()
                        logger.info(f"Email sent successfully: {queue_item.correlation_id}")
                    else:
                        raise Exception("Email sending failed")
                    
                    db.commit()
                    await message.ack()
                    
                except Exception as e:
                    logger.error(f"Failed to process email {queue_item.correlation_id}: {e}")
                    
                    # Handle retries
                    queue_item.retry_count += 1
                    queue_item.error_message = str(e)
                    
                    if queue_item.retry_count >= queue_item.max_retries:
                        queue_item.status = "failed"
                        logger.error(f"Email permanently failed: {queue_item.correlation_id}")
                        await message.ack()
                    else:
                        queue_item.status = "pending"
                        # Requeue with delay
                        await self.requeue_message(message_data, queue_item.retry_count)
                        await message.ack()
                    
                    db.commit()
                    
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await message.nack(requeue=False)
    
    async def requeue_message(self, message_data: dict, retry_count: int):
        """Requeue message with exponential backoff"""
        delay = min(300, 2 ** retry_count * 60)  # Max 5 minutes delay
        
        logger.info(f"Requeuing message {message_data['correlation_id']} with {delay}s delay")
        
        await asyncio.sleep(delay)
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

email_worker = EmailWorker()

# For running worker separately
async def main():
    worker = EmailWorker()
    await worker.start_processing()
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await worker.stop_processing()

if __name__ == "__main__":
    asyncio.run(main())