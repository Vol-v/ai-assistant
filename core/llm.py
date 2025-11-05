# core/llm.py
import json
from pydantic import BaseModel, Field,ValidationError,field_validator
from typing import Literal, Optional,List,Dict,Any
import ollama

from core.tools import TOOLS

allowed = set(TOOLS.keys())

class RunSpec(BaseModel):
    script: str = Field(..., description="The script to run")
    args: Dict[str, Any] = Field(default_factory=dict)

class ToolCall(BaseModel):
    speak_text: Optional[str] = Field(None,description="What the assistant should say. Omit if nothing to say.")
    run: Optional[RunSpec] = Field(None, description="The script to run and its arguments. Omit if no script to run.")

    @field_validator("run")
    @classmethod
    def validate_run(cls,v):
        if v not in allowed:
            raise ValueError(f"Invalid tool: {v}. Allowed tools are: {allowed}")
        return v
