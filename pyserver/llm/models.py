from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field, model_validator

# Import your generated messages once here.
# Adjust to your path, e.g.:
# from assistant.v1 import assistant_pb2 as models_pb
from protobufs.gen.py.protobufs.apis.models import task_pb2 as models_pb


class Tools(str, Enum):
    SPEAK = "speak"
    TIMER = "timer"
    PLAY_SOUND = "play_sound"


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
    play_sound: Optional[PlaySoundArgsModel] = None

    @model_validator(mode="after")
    def _validate_oneof(self) -> "ToolCallModel":
        set_count = sum(v is not None for v in (self.speak, self.timer, self.play_sound))
        if set_count != 1:
            raise ValueError("Exactly one of {'speak','timer','play_sound'} must be provided")
        return self

    @staticmethod
    def from_action(tool: Tools, args: Dict[str, Any]) -> "ToolCallModel":
        if tool == Tools.SPEAK:
            return ToolCallModel(speak=SpeakArgsModel(**args))
        if tool == Tools.TIMER:
            return ToolCallModel(timer=TimerArgsModel(**args))
        if tool == Tools.PLAY_SOUND:
            return ToolCallModel(play_sound=PlaySoundArgsModel(**args))
        raise ValueError(f"Unsupported tool: {tool}")

    def which(self) -> Tools:
        if self.speak is not None:
            return Tools.SPEAK
        if self.timer is not None:
            return Tools.TIMER
        return Tools.PLAY_SOUND

    def to_proto(self) -> models_pb.ToolCall:
        call = models_pb.ToolCall()
        if self.speak is not None:
            call.speak.CopyFrom(models_pb.SpeakArgs(**self.speak.model_dump(exclude_none=True)))
        elif self.timer is not None:
            call.timer.CopyFrom(models_pb.TimerArgs(**self.timer.model_dump(exclude_none=True)))
        else:
            call.play_sound.CopyFrom(models_pb.PlaySoundArgs(**self.play_sound.model_dump(exclude_none=True)))
        return call

    @staticmethod
    def from_proto(call_pb: models_pb.ToolCall) -> "ToolCallModel":
        which = call_pb.WhichOneof("payload")
        if which == "speak":
            return ToolCallModel(
                speak=SpeakArgsModel(
                    text=call_pb.speak.text,
                    voice_id=call_pb.speak.voice_id or None,
                )
            )
        if which == "timer":
            return ToolCallModel(
                timer=TimerArgsModel(
                    minutes=call_pb.timer.minutes,
                    label=call_pb.timer.label or None,
                )
            )
        if which == "play_sound":
            return ToolCallModel(
                play_sound=PlaySoundArgsModel(
                    sound_id=call_pb.play_sound.sound_id,
                    repeat=call_pb.play_sound.repeat or 0,
                )
            )
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

    def to_proto(self) -> models_pb.Task:
        task = models_pb.Task()
        if self.task_id:
            task.task_id = self.task_id
        task.call.CopyFrom(self.call.to_proto())
        # Map our Enum to the proto enum value (int)
        task.priority = models_pb.Priority.Value(self.priority.name)
        if self.meta:
            task.meta.update(self.meta)
        return task

    @staticmethod
    def from_proto(task_pb: models_pb.Task) -> "TaskModel":
        prio_name = models_pb.Priority.Name(task_pb.priority)
        return TaskModel(
            task_id=task_pb.task_id or None,
            call=ToolCallModel.from_proto(task_pb.call),
            priority=Priority(prio_name),
            meta=dict(task_pb.meta),
        )
