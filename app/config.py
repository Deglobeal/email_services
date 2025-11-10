import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
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
    template_service_url: str = os.getenv("TEMPLATE_SERVICE_URL", "http://localhost:8001")
    
    class Config:
        env_file = ".env"

settings = Settings()