import time
import pytest
from app.rate_limiter import TokenBucketRateLimiter


class TestRateLimiter:
    """Test token bucket rate limiter."""

    def test_allows_requests_within_limit(self):
        limiter = TokenBucketRateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.is_allowed("user1") is True

    def test_blocks_after_limit_exceeded(self):
        limiter = TokenBucketRateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False

    def test_different_users_independent(self):
        limiter = TokenBucketRateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        # user1 is at limit
        assert limiter.is_allowed("user1") is False
        # user2 should still be allowed
        assert limiter.is_allowed("user2") is True

    def test_resets_after_window(self):
        limiter = TokenBucketRateLimiter(max_requests=2, window_seconds=1)
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.is_allowed("user1") is False
        # Wait for window to expire
        time.sleep(1.1)
        assert limiter.is_allowed("user1") is True

    def test_get_remaining(self):
        limiter = TokenBucketRateLimiter(max_requests=5, window_seconds=60)
        assert limiter.get_remaining("user1") == 5
        limiter.is_allowed("user1")
        assert limiter.get_remaining("user1") == 4
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        assert limiter.get_remaining("user1") == 2

    def test_get_reset_time(self):
        limiter = TokenBucketRateLimiter(max_requests=2, window_seconds=10)
        limiter.is_allowed("user1")
        reset_time = limiter.get_reset_time("user1")
        assert 0 < reset_time <= 10

    def test_get_reset_time_no_requests(self):
        limiter = TokenBucketRateLimiter(max_requests=5, window_seconds=60)
        assert limiter.get_reset_time("user1") == 0
