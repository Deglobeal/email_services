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