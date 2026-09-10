from collections import defaultdict, deque
import hashlib
from threading import Lock
from time import monotonic

from app.core.errors import APIError


class PublicSearchRateLimiter:
    def __init__(self, limit: int = 30, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_key: str) -> None:
        client_key = hashlib.sha256(client_key.encode("utf-8")).hexdigest()
        now = monotonic()
        with self._lock:
            bucket = self._requests[client_key]
            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise APIError(status_code=429, code="RATE_LIMITED", message="Too many searches. Wait a minute and try again.")
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


suspect_search_rate_limiter = PublicSearchRateLimiter()
