from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Literal, Any

from pydantic import BaseModel, Field, model_validator


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

    # ---- Proto conversion helpers ----
    def to_proto(self, pb) -> "pb.ToolCall":
        """
        Convert to protobuf ToolCall. Pass the generated module as `pb`, e.g.:
          from assistant.v1 import assistant_pb2 as pb
          # or: from apis.models import task_pb2 as pb
        """
        call = pb.ToolCall()
        if self.speak:
            call.speak.CopyFrom(pb.SpeakArgs(text=self.speak.text, voice_id=self.speak.voice_id or ""))
        elif self.timer:
            call.timer.CopyFrom(pb.TimerArgs(minutes=self.timer.minutes, label=self.timer.label or ""))
        else:
            ps = self.play_sound
            call.play_sound.CopyFrom(pb.PlaySoundArgs(sound_id=ps.sound_id, repeat=ps.repeat or 0))
        return call

    @staticmethod
    def from_proto(call_pb) -> "ToolCallModel":
        which = call_pb.WhichOneof("payload")
        if which == "speak":
            return ToolCallModel(speak=SpeakArgsModel(text=call_pb.speak.text, voice_id=call_pb.speak.voice_id or None))
        if which == "timer":
            return ToolCallModel(timer=TimerArgsModel(minutes=call_pb.timer.minutes, label=call_pb.timer.label or None))
        if which == "play_sound":
            return ToolCallModel(play_sound=PlaySoundArgsModel(sound_id=call_pb.play_sound.sound_id, repeat=call_pb.play_sound.repeat or 0))
        raise ValueError("Empty ToolCall payload")


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

    def to_proto(self, pb) -> "pb.Task":
        task = pb.Task()
        if self.task_id:
            task.task_id = self.task_id
        task.call.CopyFrom(self.call.to_proto(pb))
        # Map Priority enum strings to proto enum values
        task.priority = getattr(pb.Priority, self.priority)
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


# Optional: a thin “plan” to collect multiple actions from the LLM
class ActionModel(BaseModel):
    tool: Literal["speak", "timer", "play_sound"]
    args: Dict[str, Any]
    when: Optional[str] = "now"  # free-form; your router parses to Trigger later

class PlanModel(BaseModel):
    actions: list[ActionModel]
    meta: Dict[str, Any] = Field(default_factory=dict)

    def to_tool_calls(self) -> list[ToolCallModel]:
        return [ToolCallModel.from_action(a.tool, a.args) for a in self.actions]