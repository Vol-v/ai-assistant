import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from protobufs.apis.models import task_pb2 as _task_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScheduleTaskRequest(_message.Message):
    __slots__ = ("task", "trigger")
    TASK_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    task: _task_pb2.Task
    trigger: _task_pb2.Trigger
    def __init__(self, task: _Optional[_Union[_task_pb2.Task, _Mapping]] = ..., trigger: _Optional[_Union[_task_pb2.Trigger, _Mapping]] = ...) -> None: ...

class ScheduleTaskResponse(_message.Message):
    __slots__ = ("task_id", "next_fire_time")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIRE_TIME_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    next_fire_time: _timestamp_pb2.Timestamp
    def __init__(self, task_id: _Optional[str] = ..., next_fire_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CancelTaskRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class CancelTaskResponse(_message.Message):
    __slots__ = ("canceled",)
    CANCELED_FIELD_NUMBER: _ClassVar[int]
    canceled: bool
    def __init__(self, canceled: bool = ...) -> None: ...

class ListTasksRequest(_message.Message):
    __slots__ = ("limit", "not_before", "include_speak", "include_timer", "include_play_sound")
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    NOT_BEFORE_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_SPEAK_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_TIMER_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_PLAY_SOUND_FIELD_NUMBER: _ClassVar[int]
    limit: int
    not_before: _timestamp_pb2.Timestamp
    include_speak: bool
    include_timer: bool
    include_play_sound: bool
    def __init__(self, limit: _Optional[int] = ..., not_before: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., include_speak: bool = ..., include_timer: bool = ..., include_play_sound: bool = ...) -> None: ...

class TaskSummary(_message.Message):
    __slots__ = ("task_id", "priority", "next_fire_time", "timezone", "tool", "meta")
    class MetaEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIRE_TIME_FIELD_NUMBER: _ClassVar[int]
    TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    TOOL_FIELD_NUMBER: _ClassVar[int]
    META_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    priority: _task_pb2.Priority
    next_fire_time: _timestamp_pb2.Timestamp
    timezone: str
    tool: str
    meta: _containers.ScalarMap[str, str]
    def __init__(self, task_id: _Optional[str] = ..., priority: _Optional[_Union[_task_pb2.Priority, str]] = ..., next_fire_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., timezone: _Optional[str] = ..., tool: _Optional[str] = ..., meta: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ListTasksResponse(_message.Message):
    __slots__ = ("tasks",)
    TASKS_FIELD_NUMBER: _ClassVar[int]
    tasks: _containers.RepeatedCompositeFieldContainer[TaskSummary]
    def __init__(self, tasks: _Optional[_Iterable[_Union[TaskSummary, _Mapping]]] = ...) -> None: ...

class GetTaskRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class GetTaskResponse(_message.Message):
    __slots__ = ("task", "trigger", "next_fire_time")
    TASK_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIRE_TIME_FIELD_NUMBER: _ClassVar[int]
    task: _task_pb2.Task
    trigger: _task_pb2.Trigger
    next_fire_time: _timestamp_pb2.Timestamp
    def __init__(self, task: _Optional[_Union[_task_pb2.Task, _Mapping]] = ..., trigger: _Optional[_Union[_task_pb2.Trigger, _Mapping]] = ..., next_fire_time: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...
