import pika, json, os
from dotenv import load_dotenv

load_dotenv()  # ✅ this loads the .env file

rabbitmq_url = os.getenv("RABBITMQ_URL")
print("RabbitMQ URL:", rabbitmq_url)  # For debugging

params = pika.URLParameters(rabbitmq_url)
connection = pika.BlockingConnection(params)
channel = connection.channel()

message = {
    "to_email": "test@example.com",
    "subject": "Test Email",
    "body": "This is a test message from RabbitMQ publisher."
}

channel.basic_publish(
    exchange='',
    routing_key='email.queue',
    body=json.dumps(message)
)

print("✅ Test message published successfully!")
connection.close()
