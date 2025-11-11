from dotenv import load_dotenv
import os

load_dotenv()

# Make sure .env is loaded correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings :
        # rabbitmq
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://iE3xhRjkn8bQHL1Z:ZLuWC7X7b5TdmseCa43AN4eB2IWy3dPD@yamanote.proxy.rlwy.net:15031/")
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:nlRajiKVwbaSkhnMDToqMTOiiKBMwkYP@postgres.railway.internal:5432/railway")
    
        # email
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", 587))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_pass: str = os.getenv("SMTP_PASS", "")
    email_from: str = os.getenv("EMAIL_FROM", "kachimaxy2@gmail")
    use_real_smtp: bool = os.getenv("USE_REAL_SMTP", "False").lower() in ("true", "1")

    
    max_retry_attempts: int = int(os.getenv("MAX_RETRY_ATTEMPTS", 5))
    redis_url: str = os.getenv("REDIS_URL", "")

    class Config:
        env_file = ".env"


settings = Settings()