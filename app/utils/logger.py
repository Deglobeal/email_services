import logging
import sys
from pythonjsonlogger import jsonlogger

def get_logger(name: str = __name__):
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s')
    log_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    return logger
