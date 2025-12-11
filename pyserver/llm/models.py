from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Literal, Any

from pydantic import BaseModel, Field, model_validator
from protobufs.gen.py.protobufs.apis.models import task_pb2 as models_pb       

# ---- Proto-parallel enums/messages ----

class Priority(str, Enum):
    PRIORITY_UNSPECIFIED = "PRIORITY_UNSPECIFIED"
    PRIORITY_HIGH = "PRIORITY_HIGH"
    PRIORITY_NORMAL = "PRIORITY_NORMAL"
    PRIORITY_LOW = "PRIORITY_LOW"


class SpeakArgsModel(BaseModel):
    text: str
    voice_id: Optional[str] = None


class TimerArgsModel(BaseModel):
    minutes: int
    label: Optional[str] = None


class PlaySoundArgsModel(BaseModel):
    sound_id: str
    repeat: Optional[int] = 0


class ToolCallModel(BaseModel):
    """
    Mirrors:
      message ToolCall {
        oneof payload {
          SpeakArgs speak = 1;
          TimerArgs timer = 2;
          PlaySoundArgs play_sound = 3;
        }
      }
    Exactly one of speak/timer/play_sound must be set.
    """
    speak: Optional[SpeakArgsModel] = None
    timer: Optional[TimerArgsModel] = None
    play_sound: Optional[PlaySoundArgsModel] = Field(default=None, alias="play_sound")

    @model_validator(mode="after")
    def _validate_oneof(self) -> "ToolCallModel":
        set_count = sum(v is not None for v in (self.speak, self.timer, self.play_sound))
        if set_count != 1:
            raise ValueError("Exactly one of {'speak','timer','play_sound'} must be provided")
        return self

    # Convenience to build from an LLM-normalized action dict
    @staticmethod
    def from_action(tool: Literal["speak", "timer", "play_sound"], args: Dict[str, Any]) -> "ToolCallModel":
        if tool == "speak":
            return ToolCallModel(speak=SpeakArgsModel(**args))
        if tool == "timer":
            return ToolCallModel(timer=TimerArgsModel(**args))
        if tool == "play_sound":
            return ToolCallModel(play_sound=PlaySoundArgsModel(**args))
        raise ValueError(f"Unsupported tool: {tool}")

    def which(self) -> Literal["speak", "timer", "play_sound"]:
        if self.speak is not None:
            return "speak"
        if self.timer is not None:
            return "timer"
        return "play_sound"

    def to_proto(self) -> models_pb.ToolCall:
        call = models_pb.ToolCall()
        if self.speak is not None:
            call.speak.CopyFrom(models_pb.SpeakArgs(**self.speak))
        elif self.timer is not None:
            call.timer.CopyFrom(models_pb.TimerArgs(**self.timer))
        else:
            call.play_sound.CopyFrom(models_pb.PlaySoundArgs(**self.play_sound))
        return call


class TaskModel(BaseModel):
    """
    Mirrors:
      message Task {
        string task_id = 1;
        ToolCall call  = 2;
        Priority priority = 3;
        map<string, string> meta = 20;
      }
    """
    task_id: Optional[str] = None
    call: ToolCallModel
    priority: Priority = Priority.PRIORITY_NORMAL
    meta: Dict[str, str] = Field(default_factory=dict)

    def to_proto(self) -> "models_pb.Task":
        task = models_pb.Task()
        if self.task_id:
            task.task_id = self.task_id
        task.call.CopyFrom(self.call.to_proto())
        # Map Priority enum strings to proto enum values
        task.priority = getattr(models_pb.Priority, self.priority)
        if self.meta:
            task.meta.update(self.meta)
        return task

    @staticmethod
    def from_proto(task_pb) -> "TaskModel":
        # Convert proto enum value back to our string Enum name
        prio_name = task_pb.Priority.Name(task_pb.priority)
        return TaskModel(
            task_id=task_pb.task_id or None,
            call=ToolCallModel.from_proto(task_pb.call),
            priority=Priority(prio_name),
            meta=dict(task_pb.meta),
        )


# a thin “plan” to collect multiple actions from the LLM
class ActionModel(BaseModel):
    tool: Literal["speak", "timer", "play_sound"]
    args: Dict[str, Any]
    when: Optional[str] = "now"  # free-form; your router parses to Trigger later

class PlanModel(BaseModel):
    actions: list[ActionModel]
    meta: Dict[str, Any] = Field(default_factory=dict)

    def to_tool_calls(self) -> list[ToolCallModel]:
        return [ToolCallModel.from_action(a.tool, a.args) for a in self.actions]