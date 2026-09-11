"""Work out which client a public request actually came from.

The public rate limiter keys on this, so getting it wrong breaks in one of two
directions and both are bad:

* Trust the peer address behind a reverse proxy and *every* citizen shares one
  bucket, because the only address the app ever sees is the proxy's. The limit
  then applies to the whole internet at once and the 31st search in a minute is
  refused for someone who has made one.
* Trust ``X-Forwarded-For`` blindly and the key becomes attacker-supplied. Any
  client can put whatever it likes in that header, so the limit stops existing
  and the limiter's own memory becomes a place to write unbounded junk.

So the header is read only as far as the number of proxies the operator says are
actually in front of the app, and never further.
"""

from __future__ import annotations

from ipaddress import IPv6Address, ip_address, ip_network

from starlette.requests import Request

UNKNOWN_CLIENT = "unknown"


def _normalise(raw: str | None) -> str | None:
    """Return a canonical key for one address, or None if it is not an address."""
    if not raw:
        return None
    try:
        address = ip_address(raw.strip())
    except ValueError:
        return None
    if isinstance(address, IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        # A single IPv6 customer is routinely handed an entire /64 and can move
        # freely inside it, so keying on the full address means an ordinary
        # connection can rotate past the limit without trying. The /64 is the
        # smallest unit that actually corresponds to one subscriber.
        return str(ip_network(f"{address}/64", strict=False))
    return str(address)


def resolve_client_key(request: Request, trusted_proxy_hops: int) -> str:
    """Identify the client, consulting X-Forwarded-For only as far as it is trusted.

    ``trusted_proxy_hops`` is the number of proxies the operator has put in front
    of this app. Zero - the default - means the header is never read at all.
    """
    peer = _normalise(request.client.host if request.client else None)
    if trusted_proxy_hops <= 0:
        return peer or UNKNOWN_CLIENT

    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [part.strip() for part in forwarded.split(",") if part.strip()]
    # Each proxy appends the address it received the request from, so the entry
    # our own proxies contributed are the rightmost ones. Counting in from the
    # right lands on the client; everything further left was supplied by the
    # caller and is ignored.
    if len(hops) < trusted_proxy_hops:
        # Fewer hops than configured: either the request reached us without
        # passing the proxy, or the hop count is wrong. Either way the header
        # cannot be trusted here, so fall back to what we can see ourselves.
        return peer or UNKNOWN_CLIENT

    candidate = _normalise(hops[-trusted_proxy_hops])
    return candidate or peer or UNKNOWN_CLIENT
