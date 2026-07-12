from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def get_client_ip(request: Request) -> str:
    """Return the real client IP, trusting X-Forwarded-For only as far back
    as settings.trusted_proxy_hops indicates.

    X-Forwarded-For is a comma-separated chain where each proxy appends the
    address of whoever connected to it: "client, proxy1, proxy2". The only
    entry we can trust is the one *our own* trusted proxy appended - anything
    to its left could have been forged by the original client. So we count
    `trusted_proxy_hops` entries in from the right, not from the left.
    """
    hops = settings.trusted_proxy_hops
    if hops > 0:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
            if parts:
                index = max(len(parts) - hops, 0)
                return parts[index]

    return get_remote_address(request)


limiter = Limiter(key_func=get_client_ip, storage_uri=settings.rate_limit_storage_uri)
