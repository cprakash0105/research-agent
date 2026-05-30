import time
import logging
from collections import defaultdict

logger = logging.getLogger("research-agent.ratelimit")


class TokenBucketRateLimiter:
    """In-memory token bucket rate limiter per user."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        """Check if a request is allowed for the given user."""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self._requests[user_id] = [
            t for t in self._requests[user_id] if t > window_start
        ]

        if len(self._requests[user_id]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            return False

        self._requests[user_id].append(now)
        return True

    def get_remaining(self, user_id: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        window_start = now - self.window_seconds
        active = [t for t in self._requests[user_id] if t > window_start]
        return max(0, self.max_requests - len(active))

    def get_reset_time(self, user_id: str) -> float:
        """Get seconds until the oldest request expires from the window."""
        if not self._requests[user_id]:
            return 0
        oldest = min(self._requests[user_id])
        reset_at = oldest + self.window_seconds
        return max(0, reset_at - time.time())


# Global rate limiter instance: 10 requests per 60 seconds per user
rate_limiter = TokenBucketRateLimiter(max_requests=10, window_seconds=60)
