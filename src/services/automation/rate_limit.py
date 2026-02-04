from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque, Dict

from core.config import get_settings


class TenantRateLimiter:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[int]] = defaultdict(deque)

    def allow(self, tenant_id: str) -> bool:
        settings = get_settings()
        now = int(datetime.now(timezone.utc).timestamp())
        window = 60
        max_events = settings.automation_rate_limit_per_minute
        queue = self._events[tenant_id]
        while queue and now - queue[0] >= window:
            queue.popleft()
        if len(queue) >= max_events:
            return False
        queue.append(now)
        return True


rate_limiter = TenantRateLimiter()
