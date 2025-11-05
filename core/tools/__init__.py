from .timer import TIMER_TOOL,TimerArgs

from pydantic import BaseModel, Field
from typing import Callable, Type

class ToolSpec(BaseModel):
    name: str
    desc: str
    args_schema: Type[BaseModel]
    run: Callable[[BaseModel], dict]  # returns a dict result for logging/summarizing


TOOLS: dict[str, ToolSpec] = {"timer": ToolSpec(
    name="timer",
    desc="A tool for measuring time intervals",
    args_schema=TimerArgs,
    run=TIMER_TOOL.set_timer
)}

__all__ = ["TOOLS"]