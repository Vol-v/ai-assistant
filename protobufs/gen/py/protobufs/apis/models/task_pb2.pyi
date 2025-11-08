import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Priority(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PRIORITY_UNSPECIFIED: _ClassVar[Priority]
    PRIORITY_HIGH: _ClassVar[Priority]
    PRIORITY_NORMAL: _ClassVar[Priority]
    PRIORITY_LOW: _ClassVar[Priority]
PRIORITY_UNSPECIFIED: Priority
PRIORITY_HIGH: Priority
PRIORITY_NORMAL: Priority
PRIORITY_LOW: Priority

class SpeakArgs(_message.Message):
    __slots__ = ("text", "voice_id")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    text: str
    voice_id: str
    def __init__(self, text: _Optional[str] = ..., voice_id: _Optional[str] = ...) -> None: ...

class TimerArgs(_message.Message):
    __slots__ = ("minutes", "label")
    MINUTES_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    minutes: int
    label: str
    def __init__(self, minutes: _Optional[int] = ..., label: _Optional[str] = ...) -> None: ...

class PlaySoundArgs(_message.Message):
    __slots__ = ("sound_id", "repeat")
    SOUND_ID_FIELD_NUMBER: _ClassVar[int]
    REPEAT_FIELD_NUMBER: _ClassVar[int]
    sound_id: str
    repeat: int
    def __init__(self, sound_id: _Optional[str] = ..., repeat: _Optional[int] = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("speak", "timer", "play_sound")
    SPEAK_FIELD_NUMBER: _ClassVar[int]
    TIMER_FIELD_NUMBER: _ClassVar[int]
    PLAY_SOUND_FIELD_NUMBER: _ClassVar[int]
    speak: SpeakArgs
    timer: TimerArgs
    play_sound: PlaySoundArgs
    def __init__(self, speak: _Optional[_Union[SpeakArgs, _Mapping]] = ..., timer: _Optional[_Union[TimerArgs, _Mapping]] = ..., play_sound: _Optional[_Union[PlaySoundArgs, _Mapping]] = ...) -> None: ...

class Recurrence(_message.Message):
    __slots__ = ("cron", "catch_up")
    CRON_FIELD_NUMBER: _ClassVar[int]
    CATCH_UP_FIELD_NUMBER: _ClassVar[int]
    cron: str
    catch_up: bool
    def __init__(self, cron: _Optional[str] = ..., catch_up: bool = ...) -> None: ...

class Trigger(_message.Message):
    __slots__ = ("at", "delay", "recurrence")
    AT_FIELD_NUMBER: _ClassVar[int]
    DELAY_FIELD_NUMBER: _ClassVar[int]
    RECURRENCE_FIELD_NUMBER: _ClassVar[int]
    at: _timestamp_pb2.Timestamp
    delay: _duration_pb2.Duration
    recurrence: Recurrence
    def __init__(self, at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., delay: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ..., recurrence: _Optional[_Union[Recurrence, _Mapping]] = ...) -> None: ...

class Task(_message.Message):
    __slots__ = ("task_id", "call", "priority", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CALL_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    call: ToolCall
    priority: Priority
    meta: _containers.ScalarMap[str, str]
    def __init__(self, task_id: _Optional[str] = ..., call: _Optional[_Union[ToolCall, _Mapping]] = ..., priority: _Optional[_Union[Priority, str]] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...
