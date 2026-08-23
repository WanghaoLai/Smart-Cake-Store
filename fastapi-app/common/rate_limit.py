"""进程内滑动窗口限流器。

每条 /chat/send 触发一次 LLM + Embedding 调用（真金白银），消息长度有界但
频率无界时，脚本化用户可直接打爆成本。单进程部署用内存滑窗即可起步；
多进程/多实例部署需换 Redis 实现（保持 allow(key) 接口不变即可平滑替换）。"""
import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(self, max_events: int, window_seconds: float):
        self.max_events = max_events
        self.window_seconds = window_seconds
        self._events: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        """窗口内第 max_events 次以内放行并记账，超出则拒绝。"""
        now = time.monotonic() if now is None else now
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.max_events:
                return False
            events.append(now)
            return True

    def reset(self, key: str) -> None:
        """清除一个主体的失败窗口。

        认证成功后账号维度应重置，否则用户正常重新登录也会被当成爆破。
        """
        with self._lock:
            self._events.pop(key, None)
