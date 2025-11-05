from .timer import Timer

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
    args_schema=BaseModel,
    run=Timer.set_timer #obviously not correct but serves as a placeholder
)}

__all__ = ["TOOLS"]