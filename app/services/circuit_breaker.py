import time
from app.utils.logger import get_logger

logger = get_logger("circuit_breaker")

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_time=30):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning({"status": "circuit_open", "failures": self.failures})

    def allow_request(self):
        if self.state == "OPEN":
            if (time.time() - self.last_failure_time) > self.recovery_time: # type: ignore 
                self.state = "HALF-OPEN"
                logger.info({"status": "circuit_half_open"})
                return True
            else:
                return False
        return True
