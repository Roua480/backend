import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .config import settings

WINDOW_SECONDS = 60
_buckets: dict[str, deque[float]] = defaultdict(deque)


async def rate_limit(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    now = time.time()
    dq = _buckets[client]
    while dq and now - dq[0] > WINDOW_SECONDS:
        dq.popleft()
    dq.append(now)
    if len(dq) > settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )

