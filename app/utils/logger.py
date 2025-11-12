import logging
from pythonjsonlogger import jsonlogger

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = jsonlogger.JsonFormatter( # type: ignore
            '%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
