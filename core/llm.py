# core/llm.py
import json
from pydantic import ValidationError
from .contracts import Plan
from .tools import TOOLS
import ollama
from pathlib import Path

def _system_prompt() -> str:
    system = Path("data/prompts/system.txt").read_text()
    # Inject allowlisted tool names: timer, system_info, etc.
    allowed = ", ".join(sorted(TOOLS.keys()))
    return system.replace("{ALLOWED_TOOLS}", allowed)

def plan_from_text(user_text: str, model: str = "llama3.1:8b-instruct") -> Plan:
    sys = _system_prompt()
    messages = [
        {"role": "system", "content": sys},
        {"role": "user", "content": user_text},
    ]
    res = ollama.chat(model=model, messages=messages)
    raw = res["message"]["content"]

    # Must be pure JSON per contract; parse + validate
    try:
        obj = json.loads(raw)
        parsed = Plan.model_validate(obj)  # this also checks scripts against TOOLS
        return parsed
    except (json.JSONDecodeError, ValidationError):
        # Failsafe: say a short fallback and do nothing
        return Plan(speak_text="Sorry, I didnt get that.", runs=[])
