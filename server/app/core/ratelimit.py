"""登录 / 注册限速：单实例内存滑动窗口（架构文档 4.8）。"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.errors import C, err


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and q[0] <= now - self._window:
            q.popleft()
        if len(q) >= self._limit:
            raise err(C.RATE_LIMITED, "请求过于频繁，请稍后再试")
        q.append(now)
