import asyncio
from core.events import Event

class EventBus:
    def __init__(self):
        self.queue: asyncio.Queue[Event] = asyncio.Queue()

    async def put(self,ev: Event):
        await self.queue.put(ev)

    async def get(self) -> Event:
        return await self.queue.get()