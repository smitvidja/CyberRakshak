"""A bounded, in-process rate limiter for unauthenticated endpoints.

Two things about it are deliberate and worth stating, because both are the kind
of detail that looks like an omission later:

* **It is per process.** One process is what this project deploys (a single
  Render instance running one uvicorn worker), so a shared counter would add a
  database write to a public hot path to solve a problem the deployment does not
  have. Run more than one worker or instance and the effective limit multiplies
  by that count - see ``docs/DEPLOYMENT.md``.
* **It tracks a bounded number of clients.** The old version kept a dict entry
  per client key forever, so memory grew with the number of distinct addresses
  ever seen and never came back. That was already a slow leak; once the key can
  come from ``X-Forwarded-For`` it is a caller-controlled one.
"""

from collections import OrderedDict, deque
import hashlib
from threading import Lock
from time import monotonic

from app.core.errors import APIError

# Enough that a real audience is never evicted, small enough that a full table is
# a few megabytes rather than however much a caller felt like sending.
DEFAULT_MAX_TRACKED_CLIENTS = 20_000


class PublicSearchRateLimiter:
    def __init__(
        self,
        limit: int = 30,
        window_seconds: int = 60,
        max_tracked_clients: int = DEFAULT_MAX_TRACKED_CLIENTS,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_tracked_clients = max_tracked_clients
        # Ordered by least-recently-touched, so eviction has an obvious victim.
        self._requests: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    def check(self, client_key: str) -> None:
        digest = hashlib.sha256(client_key.encode("utf-8")).hexdigest()
        now = monotonic()
        with self._lock:
            bucket = self._requests.get(digest)
            if bucket is None:
                self._evict(now)
                bucket = deque()
                self._requests[digest] = bucket
            self._requests.move_to_end(digest)

            while bucket and bucket[0] <= now - self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise APIError(
                    status_code=429,
                    code="RATE_LIMITED",
                    message="Too many searches. Wait a minute and try again.",
                )
            bucket.append(now)

    def _evict(self, now: float) -> None:
        """Make room for one new client. Caller holds the lock."""
        if len(self._requests) < self.max_tracked_clients:
            return
        cutoff = now - self.window_seconds
        # Drop clients whose whole window has passed first: they are finished
        # with, so removing them costs nothing and is not a bypass.
        expired = [key for key, bucket in self._requests.items() if not bucket or bucket[-1] <= cutoff]
        for key in expired:
            del self._requests[key]
        # If every tracked client is still inside its window the table is full of
        # live traffic, and something has to go. The least-recently-seen client is
        # the one closest to expiring anyway. This is the honest cost of a bounded
        # table: a caller cycling through addresses fast enough can push others
        # out and regain a fresh allowance. Bounded memory is worth more than a
        # limit that holds perfectly right up until the process is killed.
        while len(self._requests) >= self.max_tracked_clients:
            self._requests.popitem(last=False)

    @property
    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._requests)

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


suspect_search_rate_limiter = PublicSearchRateLimiter()
# Corrections are an unauthenticated write, so they get their own, tighter budget.
# Sharing the search limiter's bucket would let a flood of corrections lock a
# citizen out of searching, and vice versa.
suspect_correction_rate_limiter = PublicSearchRateLimiter(limit=5, window_seconds=60)
