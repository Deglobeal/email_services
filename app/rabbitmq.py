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
            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)  #type: ignore
            self.channel = await self.connection.channel()  #type: ignore
            
            # Set prefetch count
            await self.channel.set_qos(prefetch_count=10)       #type: ignore
            
            # Declare exchange
            self.exchange = await self.channel.declare_exchange(        #type: ignore
                "notifications.direct",
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Declare queues with dead letter exchange
            self.queues['email'] = await self.channel.declare_queue( #type: ignore
                "email.queue",
                durable=True,
                arguments={
                    'x-dead-letter-exchange': 'notifications.direct',
                    'x-dead-letter-routing-key': 'failed.queue'
                }
            )
            
            self.queues['failed'] = await self.channel.declare_queue( #type: ignore
                "failed.queue",
                durable=True
            )
            
            # Bind queues to exchange
            await self.queues['email'].bind(self.exchange, routing_key="email")
            await self.queues['failed'].bind(self.exchange, routing_key="failed")
            
            logger.info("RabbitMQ connection established and queues declared")
            
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
            headers={
                'x-correlation-id': message.get('correlation_id', ''),
                'x-retry-count': 0
            }
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
        try:
            original_message = json.loads(message.body.decode())
            failed_message = {
                'original_message': original_message,
                'error': error,
                'failed_at': time.time(), # type: ignore
                'retry_count': message.headers.get('x-retry-count', 0)
            }
            
            failed_message_body = json.dumps(failed_message).encode()
            failed_rabbitmq_message = aio_pika.Message(
                body=failed_message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )
            
            await self.exchange.publish(
                failed_rabbitmq_message,
                routing_key="failed"
            )
            
            await message.ack()
            logger.warning(f"Message moved to failed queue: {original_message.get('correlation_id')}")
            
        except Exception as e:
            logger.error(f"Failed to move message to failed queue: {e}")
            await message.nack(requeue=False)

rabbitmq_manager = RabbitMQManager()