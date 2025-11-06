

from dataclasses import dataclass, field

@dataclass
class Event:
    kind: str
    payload: dict = field(default_factory=dict)