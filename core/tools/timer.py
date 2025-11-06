#timer functionality implementation

import asyncio
import threading
import time
from typing import Any, Awaitable, Callable, Optional, Union
from pydantic import BaseModel

class TimerArgs(BaseModel):
    minutes: int  # duration in minutes

ExpireCallback = Callable[[int], Awaitable[Any]]


class Timer:    
    def __init__(self,on_expire: Optional[ExpireCallback] = None):
        self._task: Optional[asyncio.Task] = None
        self._duration: int = 0  # duration in seconds
        self._started_at: float = 0.0
        self._on_expire = on_expire
    

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()
    
    def remaining(self) -> float:
        if not self.is_running():
            return 0.0
        elapsed = time.monotonic() - self._started_at
        return max(0.0, self._duration - elapsed)
    
    def cancel_timer(self) -> dict:
        if self._task and not self._task.done():
            self._task.cancel()
            return {"ok": True, "canceled": True}
        return {"ok": True, "canceled": False, "reason": "no_active_timer"}
    
    def set_timer(self, args: TimerArgs) -> dict:
        if self._on_expire is None:
            raise RuntimeError("Timer on_expire callback is not set")

        # Replace any existing timer TODO: do we need multiple timers?
        self.cancel_timer()

        self._minutes = int(args.minutes)
        self._duration_s = float(self._minutes * 60)
        self._started_at = time.monotonic()

        async def _run():
            try:
                await asyncio.sleep(self._duration_s)
            except asyncio.CancelledError:
                return
            await self._on_expire(self._minutes)

        self._task = asyncio.create_task(_run(), name=f"timer_{self._minutes}m")

        return {"ok": True, "scheduled_minutes": self._minutes}

TIMER_TOOL = Timer()