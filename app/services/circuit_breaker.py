import time
from typing import Callable
from app.utils.logger import get_logger

logger = get_logger("circuit_breaker")

class SimpleCircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_seconds=60):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.fail_count = 0
        self.opened_at = None

    def record_failure(self):
        self.fail_count += 1
        if self.fail_count >= self.failure_threshold:
            self.opened_at = time.time()
            logger.warning("circuit_opened", extra={"fail_count": self.fail_count})

    def record_success(self):
        self.fail_count = 0
        self.opened_at = None

    def is_open(self):
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.recovery_seconds:
            # half-open / attempt recovery
            self.fail_count = 0
            self.opened_at = None
            return False
        return True
