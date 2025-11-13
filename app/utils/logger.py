import logging
import os
import sys
import uuid
from logging.handlers import RotatingFileHandler
from pythonjsonlogger.json import JsonFormatter
from colorama import Fore, Style, init
from typing import Optional

# Initialize color output for Windows terminals
init(autoreset=True)

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# 🎨 Colorized console formatter
class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        message = super().format(record)
        return f"{color}{message}{Style.RESET_ALL}"


# 🧩 Thread-local request context
class RecordContext:
    """Stores request-specific data like request_id."""
    def __init__(self):
        self._request_id: Optional[str] = None

    @property
    def request_id(self) -> Optional[str]:
        return self._request_id

    @request_id.setter
    def request_id(self, value: Optional[str]):
        self._request_id = value


record_context = RecordContext()


def set_request_id(request_id: Optional[str] = None):
    """Attach a request ID for current request logs."""
    record_context.request_id = request_id or str(uuid.uuid4())


def clear_request_id():
    """Clear after request completes."""
    record_context.request_id = None


# 🧾 JSON structured formatter
class CustomJsonFormatter(JsonFormatter):
    def process_log_record(self, log_data: dict) -> dict:
        """Add custom fields to every JSON log record."""
        log_data["service"] = "email_service_app"
        log_data["request_id"] = record_context.request_id
        return log_data


# 🧠 Logger factory
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # 🎨 Console handler (colorized output)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            ColorFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )

        # 🧾 Structured JSON log file
        json_file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "structured_logs.json"),
            maxBytes=10_000_000,
            backupCount=60,
        )
        json_formatter = CustomJsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        json_file_handler.setFormatter(json_formatter)

        # ⚠️ Dedicated error-only log file
        error_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "consumer_errors.log"),
            maxBytes=5_000_000,
            backupCount=30,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )

        logger.addHandler(console_handler)
        logger.addHandler(json_file_handler)
        logger.addHandler(error_handler)

    return logger
