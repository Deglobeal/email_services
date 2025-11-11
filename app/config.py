from dotenv import load_dotenv
import os

load_dotenv()

class Settings:

    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost/")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/email_db")
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.example.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", 587))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    email_from: str = os.getenv("EMAIL_FROM", "no-reply@example.com")
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", 5))
    redis_url: str = os.getenv("REDIS_URL", "")

settings = Settings()