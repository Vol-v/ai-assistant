# core/llm.py
import json
from pathlib import Path

import ollama
from pydantic import ValidationError

from pyserver.llm.models import ToolCallModel, Tools, SpeakArgsModel


def _system_prompt() -> str:
    system = Path("data/prompts/system.txt").read_text()
    # Use enum *values* ("speak", "timer", "play_sound"), not names ("SPEAK", ...)
    allowed = ", ".join(sorted(t.value for t in Tools))
    return system.replace("{ALLOWED_TOOLS}", allowed)


def toolcall_from_text(user_text: str, model: str = "llama3.1:8b-instruct") -> ToolCallModel:
    sys = _system_prompt()
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_text},
    ]
    res = ollama.chat(model=model, messages=messages)
    raw = res["message"]["content"]

    try:
        obj = json.loads(raw)
        # LLM should output JSON matching ToolCallModel schema
        parsed = ToolCallModel.model_validate(obj)
        return parsed
    except (json.JSONDecodeError, ValidationError):
        # Failsafe: just speak an apology, no tools
        return ToolCallModel(
            speak=SpeakArgsModel(text="Sorry, I didn’t catch that.").model_dump()
        )
