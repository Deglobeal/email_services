import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    database_url: str =os.getenv("DATABASE_URL")

    # REDIS
    redis_url: str = os.getenv("REDIS_URL")

    # RabbitMQ
    rabbitmq_url: str = os.getenv("RABBITMQ_URL")

    # email
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")

    # Service URLs
    api_gateway_url: str = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    class Config:
        env_file = ".env"

settings = Settings()