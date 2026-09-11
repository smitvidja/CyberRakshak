"""Rate-limiter correctness: who a request is attributed to, and what that costs in memory.

The behaviour these lock down is the behaviour that was wrong: the limiter keyed on
``request.client.host``, which behind a reverse proxy is the proxy - identical for
every citizen - and it kept one dict entry per key forever.
"""

from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.client_identity import resolve_client_key
from app.core.public_rate_limit import PublicSearchRateLimiter


def _request(peer: str | None, forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded is not None else []
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/suspects/search",
        "headers": headers,
        "client": (peer, 51234) if peer else None,
        "scheme": "http",
        "server": ("testserver", 80),
        "query_string": b"",
        "root_path": "",
    }
    request = Request(scope)
    assert request.headers == Headers(scope=scope)
    return request


# --------------------------------------------------------------- client attribution

def test_two_citizens_behind_one_proxy_are_not_the_same_client() -> None:
    """The defect this fixes: one shared bucket for the entire internet.

    Behind a proxy the peer address is the proxy for everybody, so keying on it
    put every citizen in one bucket and the 31st search in a minute was refused
    for someone who had made one.
    """
    proxy = "10.0.0.7"
    first = resolve_client_key(_request(proxy, "203.0.113.5"), trusted_proxy_hops=1)
    second = resolve_client_key(_request(proxy, "203.0.113.6"), trusted_proxy_hops=1)
    assert first != second
    assert first == "203.0.113.5"
    assert second == "203.0.113.6"


def test_the_header_is_ignored_when_no_proxy_is_declared() -> None:
    """Default configuration must not let a caller choose its own bucket."""
    key = resolve_client_key(_request("198.51.100.9", "203.0.113.5"), trusted_proxy_hops=0)
    assert key == "198.51.100.9"


def test_a_caller_cannot_widen_its_allowance_by_prepending_hops() -> None:
    """Everything left of the trusted hop count is caller-supplied and must not count."""
    real_client = "203.0.113.5"
    honest = resolve_client_key(_request("10.0.0.7", real_client), trusted_proxy_hops=1)
    spoofed = resolve_client_key(
        _request("10.0.0.7", f"1.2.3.4, 5.6.7.8, {real_client}"), trusted_proxy_hops=1
    )
    assert spoofed == honest == real_client


def test_two_trusted_proxies_count_in_from_the_right() -> None:
    key = resolve_client_key(
        _request("10.0.0.7", "203.0.113.5, 10.0.0.3"), trusted_proxy_hops=2
    )
    assert key == "203.0.113.5"


def test_a_short_header_falls_back_to_the_peer_rather_than_the_leftmost_entry() -> None:
    """A request that skipped the proxy must not get to name itself."""
    key = resolve_client_key(_request("198.51.100.9", "203.0.113.5"), trusted_proxy_hops=2)
    assert key == "198.51.100.9"


def test_a_junk_header_falls_back_to_the_peer() -> None:
    key = resolve_client_key(_request("198.51.100.9", "not-an-address"), trusted_proxy_hops=1)
    assert key == "198.51.100.9"


def test_a_missing_header_falls_back_to_the_peer() -> None:
    key = resolve_client_key(_request("198.51.100.9"), trusted_proxy_hops=1)
    assert key == "198.51.100.9"


def test_an_unidentifiable_client_still_produces_a_key() -> None:
    assert resolve_client_key(_request(None), trusted_proxy_hops=0) == "unknown"


def test_ipv6_is_limited_per_subscriber_prefix_not_per_address() -> None:
    """One IPv6 customer holds a whole /64 and can rotate inside it at will."""
    first = resolve_client_key(_request("2001:db8:abcd:1234::1"), trusted_proxy_hops=0)
    second = resolve_client_key(_request("2001:db8:abcd:1234::99ff"), trusted_proxy_hops=0)
    other = resolve_client_key(_request("2001:db8:abcd:5678::1"), trusted_proxy_hops=0)
    assert first == second, "addresses in one /64 are one subscriber"
    assert first != other, "a different /64 is a different subscriber"


def test_an_ipv4_mapped_address_keys_the_same_as_the_plain_address() -> None:
    mapped = resolve_client_key(_request("::ffff:203.0.113.5"), trusted_proxy_hops=0)
    plain = resolve_client_key(_request("203.0.113.5"), trusted_proxy_hops=0)
    assert mapped == plain


# ------------------------------------------------------------------- the limit itself

def test_the_limit_is_enforced_per_client() -> None:
    limiter = PublicSearchRateLimiter(limit=2, window_seconds=60)
    limiter.check("203.0.113.5")
    limiter.check("203.0.113.5")
    # A different client is unaffected by the first one's spending.
    limiter.check("203.0.113.6")
    try:
        limiter.check("203.0.113.5")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
        assert getattr(exc, "code", None) == "RATE_LIMITED"
    else:
        raise AssertionError("expected the third request to be refused")


def test_the_window_slides_so_an_allowance_comes_back() -> None:
    limiter = PublicSearchRateLimiter(limit=1, window_seconds=0)
    limiter.check("203.0.113.5")
    limiter.check("203.0.113.5")  # the first entry has already aged out


# ------------------------------------------------------------------ bounded memory

def test_tracking_is_bounded_no_matter_how_many_clients_appear() -> None:
    """The old limiter kept an entry per client key forever.

    Once the key can come from a header, that is a caller-controlled allocation.
    """
    limiter = PublicSearchRateLimiter(limit=5, window_seconds=60, max_tracked_clients=50)
    for index in range(5_000):
        limiter.check(f"198.51.100.{index // 250}:{index}")
    assert limiter.tracked_clients <= 50


def test_quiet_clients_are_evicted_before_an_active_one() -> None:
    """Eviction order is the guarantee, not survival.

    A bounded table under sustained new arrivals must drop somebody; what it must
    not do is drop the client that is currently spending its allowance while
    clients that have gone quiet are still taking up room.
    """
    limiter = PublicSearchRateLimiter(limit=3, window_seconds=60, max_tracked_clients=10)
    for index in range(9):
        limiter.check(f"192.0.2.{index}")
    busy = "203.0.113.200"
    limiter.check(busy)
    limiter.check(busy)

    # Five new arrivals against nine quiet clients: there is room to evict without
    # reaching the active one.
    for index in range(20, 25):
        limiter.check(f"192.0.2.{index}")

    # The busy client has spent 2 of 3. If its bucket had been evicted it would
    # have a fresh allowance and the fourth call below would pass.
    limiter.check(busy)
    try:
        limiter.check(busy)
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 429
    else:
        raise AssertionError("the active client's bucket was lost to eviction")


def test_sustained_new_arrivals_do_eventually_reclaim_an_active_client() -> None:
    """The cost of a bounded table, asserted rather than left as a surprise.

    A caller working through enough distinct addresses can push an existing client
    out and so hand itself a fresh allowance. That is inherent to bounding the
    table, and it costs real addresses now that the key cannot come from a header.
    """
    limiter = PublicSearchRateLimiter(limit=3, window_seconds=60, max_tracked_clients=10)
    busy = "203.0.113.200"
    limiter.check(busy)
    limiter.check(busy)
    limiter.check(busy)  # allowance now spent

    for index in range(100):
        limiter.check(f"192.0.2.{index}")

    # Evicted, so the allowance is fresh again. Documented, not hidden.
    limiter.check(busy)
    assert limiter.tracked_clients <= 10


# ------------------------------------------------------------------ through the API

def test_the_corrections_endpoint_enforces_its_own_budget(api_client) -> None:
    """Corrections are an unauthenticated write and had no limit at all.

    It also gets a separate budget from search, so flooding one cannot lock a
    citizen out of the other.
    """
    from app.core.public_rate_limit import suspect_correction_rate_limiter

    client, _ = api_client
    body = {
        "identifier_type": "UPI",
        "identifier_value": "limit-check@upi",
        "reason": "This identifier belongs to me and the signal appears incorrect.",
    }
    limit = suspect_correction_rate_limiter.limit
    for _ in range(limit):
        assert client.post("/api/v1/suspects/corrections", json=body).status_code == 201

    refused = client.post("/api/v1/suspects/corrections", json=body)
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "RATE_LIMITED"

    # Search has its own bucket and is untouched by the flood above.
    search = client.post(
        "/api/v1/suspects/search",
        json={"identifier_type": "UPI", "identifier_value": "limit-check@upi"},
    )
    assert search.status_code == 200
