
import asyncio
from dataclasses import field
import heapq
import time
from typing import Any, Callable


class _Scheduled:
    due: float
    fn: Callable[[], Any] = field(compare=False)

class Scheduler:
    def __init__(self):
        self._heap: list[_Scheduled] = []
        self._stop = False
    
    def stop(self):
        self._stop = True
    

    def at(self,epoch:float,fn: Callable[[],Any]):
        heapq.heappush(self._heap,_Scheduled(due=epoch,fn=fn))

    def in_(self,seconds:float,fn: Callable[[],Any]):
        self.at(time.monotonic()+seconds,fn)

    async def run(self):
        while not self._stop:
            now = time.monotonic()
            while self._heap and self._heap[0].due <= now:
                job = heapq.heappop(self._heap)
                try:
                    job.fn()
                except Exception as e:
                    # No bus here—leave logging to caller
                    print(f"[scheduler] job error: {e}")
            await asyncio.sleep(0.05)
