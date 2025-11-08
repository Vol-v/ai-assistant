from protobufs.apis.models import task_pb2 as _task_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RunTaskRequest(_message.Message):
    __slots__ = ("call",)
    CALL_FIELD_NUMBER: _ClassVar[int]
    call: _task_pb2.ToolCall
    def __init__(self, call: _Optional[_Union[_task_pb2.ToolCall, _Mapping]] = ...) -> None: ...

class RunTaskResponse(_message.Message):
    __slots__ = ("status", "error_message", "output")
    class Status(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        STATUS_UNSPECIFIED: _ClassVar[RunTaskResponse.Status]
        STATUS_OK: _ClassVar[RunTaskResponse.Status]
        STATUS_FAILED: _ClassVar[RunTaskResponse.Status]
    STATUS_UNSPECIFIED: RunTaskResponse.Status
    STATUS_OK: RunTaskResponse.Status
    STATUS_FAILED: RunTaskResponse.Status
    class OutputEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    status: RunTaskResponse.Status
    error_message: str
    output: _containers.ScalarMap[str, str]
    def __init__(self, status: _Optional[_Union[RunTaskResponse.Status, str]] = ..., error_message: _Optional[str] = ..., output: _Optional[_Mapping[str, str]] = ...) -> None: ...
