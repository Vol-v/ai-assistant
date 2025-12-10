from __future__ import annotations

import asyncio
import datetime as dt
import re
from typing import Optional, Dict, Any, Sequence

import grpc


import protobufs.gen.py.protobufs.apis.services.scheduler_api_pb2 as sched_pb
import protobufs.gen.py.protobufs.apis.services.scheduler_api_pb2_grpc as sched_rpc
import protobufs.gen.py.protobufs.apis.models.task_pb2 as models_pb

# Your Pydantic models from the previous step
from .models import ToolCallModel, TaskModel, PlanModel, Priority


class SchedulerClient:
    """Thin async client for the Go SchedulerService."""

    def __init__(self, address: str = "127.0.0.1:50070", *, secure: bool = False):
        self._address = address
        self._secure = secure
        self._channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[sched_rpc.SchedulerServiceStub] = None

    async def __aenter__(self) -> "SchedulerClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def start(self) -> None:
        if self._channel is None:
            if self._secure:
                # TODO: load real creds later via envs
                self._channel = grpc.aio.secure_channel(self._address, grpc.local_channel_credentials())
            else:
                self._channel = grpc.aio.insecure_channel(self._address)
            self._stub = sched_rpc.SchedulerServiceStub(self._channel)

    async def close(self) -> None:
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None


    async def schedule_toolcall(
        self,
        call: ToolCallModel,
        *,
        when: str | dt.datetime | dt.timedelta | None = "now",
        priority: Priority = Priority.PRIORITY_NORMAL,
        timezone: str = "Asia/Nicosia",
        meta: Optional[Dict[str, str]] = None,
        task_id: Optional[str] = None,
    ) -> sched_pb.ScheduleTaskResponse:
        """
        Convert a ToolCallModel into Task and call ScheduleTask.
        """
        assert self._stub is not None, "call start() first"

        # Build protobuf Task
        task_model = TaskModel(task_id=task_id, call=call, priority=priority, meta=meta or {})
        task_pb = task_model.to_proto(models_pb)


        req = sched_pb.ScheduleTaskRequest(task=task_pb)
        return await self._stub.ScheduleTask(req)

    async def schedule_plan(
        self,
        plan: PlanModel,
        *,
        timezone: str = "Asia/Nicosia",
        default_priority: Priority = Priority.PRIORITY_NORMAL,
    ) -> Sequence[sched_pb.ScheduleTaskResponse]:
        """
        Take your LLM PlanModel (array of actions), coerce to ToolCalls + Triggers, schedule all.
        """
        results = []
        for action in plan.actions:
            call = ToolCallModel.from_action(action.tool, action.args)
            resp = await self.schedule_toolcall(
                call,
                when=action.when or "now",
                priority=default_priority,
                timezone=timezone,
            )
            results.append(resp)
        return results
