# listener/daemon.py
from __future__ import annotations
from typing import Optional
import re

import grpc

from protobufs.gen.py.protobufs.apis.models import task_pb2 as models_pb             
from protobufs.gen.py.protobufs.apis.services import scheduler_api_pb2 as sched_pb          
from protobufs.gen.py.protobufs.apis.services import scheduler_api_pb2_grpc as sched_rpc    
from google.protobuf.duration_pb2 import Duration

from llm.models import TaskModel, ToolCallModel

class SchedulerClient:
    def __init__(self, addr: str, secure: bool = False):
        self._addr = addr
        self._secure = secure
        self._ch: Optional[grpc.aio.Channel] = None
        self._stub: Optional[sched_rpc.SchedulerServiceStub] = None

    async def __aenter__(self) -> "SchedulerClient":
        await self.start(); return self
    
    async def __aexit__(self, *_): await self.close()

    async def start(self):
        if self._ch is None:
            self._ch = grpc.aio.secure_channel(self._addr, grpc.local_channel_credentials()) if self._secure \
                       else grpc.aio.insecure_channel(self._addr)
            self._stub = sched_rpc.SchedulerServiceStub(self._ch)

    async def close(self):
        if self._ch:
            await self._ch.close()
            self._ch = None
            self._stub = None

    async def schedule_toolcall_now(self, call: ToolCallModel, *, timezone: Optional[str] = None) -> sched_pb.ScheduleTaskResponse:
        assert self._stub is not None
        # Build Task
        task = models_pb.Task()
        task.call.CopyFrom(call.to_proto())

        task.priority = models_pb.PRIORITY_NORMAL

        # Trigger: now (delay=0)
        trig = models_pb.Trigger()
        d = Duration(); d.FromSeconds(0)
        trig.delay.CopyFrom(d)

        req = sched_pb.ScheduleTaskRequest(task=task, trigger=trig)
        return await self._stub.ScheduleTask(req)


    async def schedule_timer(self, toolcall: ToolCallModel, minutes: int) -> sched_pb.ScheduleTaskResponse:
        """Schedule a timer toolcall to fire after N minutes."""
        assert self._stub is not None
        task_model = TaskModel(call=toolcall)
        task_pb = task_model.to_proto()

        # Build Task
        task = models_pb.Task()
        task.call.CopyFrom(toolcall.to_proto())

        trig = models_pb.Trigger()
        d = Duration(); d.FromSeconds(max(0, minutes * 60))
        trig.delay.CopyFrom(d)

        req = sched_pb.ScheduleTaskRequest(task=task, trigger=trig)
        assert self._stub is not None
        return await self._stub.ScheduleTask(req)