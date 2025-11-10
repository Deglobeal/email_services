import aio_pika
import json
import logging
from typing import Callable, Optional
from app.config import settings

logger = logging.getLogger(__name__)

class RabbitMQManager:
    def __init__(self):
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queues = {}
    
    async def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url) # 
            self.channel = await self.connection.channel()
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                "notifications.direct",
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )

            # Declare queues
            self.queues['email'] = await self.channel.declare_queue(
                "email.queue",
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'notifications.direct',
                    'x-dead-letter-routing-key': 'failed.queue'
                }
            )
            
            self.queues['failed'] = await self.channel.declare_queue( 
                "failed.queue",
                durable=True
            )

            # Bind queues to exchange
            await self.queues['email'].bind(self.exchange, routing_key="email")
            await self.queues['failed'].bind(self.exchange, routing_key="failed")
            
            logger.info("RabbitMQ connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def publish_email_message(self, message: dict):
        """Publish message to email queue"""
        if not self.channel:
            await self.connect()
        
        message_body = json.dumps(message).encode()
        rabbitmq_message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers=message.get('headers', {})
        )
        
        await self.exchange.publish(
            rabbitmq_message,
            routing_key="email"
        )
        logger.info(f"Message published to email queue: {message.get('correlation_id')}")
    
    async def consume_email_messages(self, callback: Callable):
        """Consume messages from email queue"""
        if not self.queues.get('email'):
            await self.connect()
        
        await self.queues['email'].consume(callback)
        logger.info("Started consuming email queue messages")
    
    async def move_to_failed_queue(self, message: aio_pika.IncomingMessage, error: str):
        """Move failed message to dead letter queue"""
        failed_message = {
            'original_message': message.body.decode(),
            'error': error,
            'failed_at': str(message.headers.get('failed_at'))
        }

        await self.publish_failed_message(failed_message)
        await message.ack()
    
    async def publish_failed_message(self, message: dict):
        """Publish message to failed queue"""
        message_body = json.dumps(message).encode()
        rabbitmq_message = aio_pika.Message(
            body=message_body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        
        await self.exchange.publish(
            rabbitmq_message,
            routing_key="failed"
        )

rabbitmq_manager = RabbitMQManager()

