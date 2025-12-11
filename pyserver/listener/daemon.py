# listener/daemon.py
from __future__ import annotations
import asyncio
import enum
import logging
from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, Tuple
import re

import grpc

from protobufs.gen.py.protobufs.apis.models import task_pb2 as models_pb             
from protobufs.gen.py.protobufs.apis.services import scheduler_api_pb2 as sched_pb          
from protobufs.gen.py.protobufs.apis.services import scheduler_api_pb2_grpc as sched_rpc    
from google.protobuf.duration_pb2 import Duration

from llm.models import ToolCallModel, PlanModel, ActionModel
AudioFrame = bytes

class WakeDetector(Protocol):
    async def wait_for_hotword(self) -> None: ...

class VAD(Protocol):
    async def stream_until_eou(self, pre_roll: Sequence[AudioFrame]) -> Sequence[AudioFrame]: ...

class ASR(Protocol):
    async def transcribe(self, frames: Sequence[AudioFrame]) -> Tuple[str, float]: ...

class Planner(Protocol):
    async def plan(self, transcript: str, summary_hint: Optional[str] = None) -> PlanModel: ...

# ===============================
#       Mock implementations
# ===============================
class MockWakeDetector:
    async def wait_for_hotword(self) -> None:
        print("\n[Wake] Press ENTER to wake…", flush=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, input)

class MockVAD:
    async def stream_until_eou(self, pre_roll: Sequence[AudioFrame]) -> Sequence[AudioFrame]:
        print("[VAD] Type your utterance and press ENTER:")
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, input)
        return [text.encode("utf-8")]

class MockASR:
    async def transcribe(self, frames: Sequence[AudioFrame]) -> Tuple[str, float]:
        txt = (frames[0].decode("utf-8").strip() if frames else "")
        logging.getLogger("ASR").info("Transcript: %r", txt)
        return txt, (0.95 if txt else 0.0)

class MockPlanner:
    async def plan(self, transcript: str, summary_hint: Optional[str] = None) -> PlanModel:
        t = transcript.lower()
        actions: list[ActionModel] = []
        if "timer" in t:
            m = re.search(r"(\d+)", t)
            mins = int(m.group(1)) if m else 10
            actions.append(ActionModel(tool="speak", args={"text": f"Okay, setting a {mins} minute timer."}, when="now"))
            actions.append(ActionModel(tool="timer", args={"minutes": mins, "label": "timer"}, when=f"in {mins} minutes"))
        elif "sound" in t:
            actions.append(ActionModel(tool="speak", args={"text": "Playing a sound."}, when="now"))
            actions.append(ActionModel(tool="play_sound", args={"sound_id": "ding", "repeat": 1}, when="now"))
        else:
            actions.append(ActionModel(tool="speak", args={"text": f"You said: {transcript}"}, when="now"))
        return PlanModel(actions=actions)

# ===============================
#       Scheduler gRPC client
# ===============================
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

    async def schedule_toolcall_when(self, call: ToolCallModel, when: str, *, timezone: Optional[str] = None) -> sched_pb.ScheduleTaskResponse:
        """
        Minimal natural 'when' support for now:
          - "now"
          - "in N seconds/minutes/hours"
        Everything else falls back to now.
        """
        if when is None or when.strip().lower() == "now":
            return await self.schedule_toolcall_now(call, timezone=timezone)

        # Very small "in N X" parser
        m = re.match(r"in\s+(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hour|hours)\b", when.strip().lower())
        seconds = 0
        if m:
            n = int(m.group(1)); unit = m.group(2)[0]
            if unit == "s": seconds = n
            elif unit == "m": seconds = n * 60
            elif unit == "h": seconds = n * 3600

        # Build Task
        task = models_pb.Task()
        task.call.CopyFrom(call.to_proto())

        trig = models_pb.Trigger()
        d = Duration(); d.FromSeconds(max(0, seconds))
        trig.delay.CopyFrom(d)

        req = sched_pb.ScheduleTaskRequest(task=task, trigger=trig)
        assert self._stub is not None
        return await self._stub.ScheduleTask(req)

# ===============================
#              FSM
# ===============================
class State(enum.Enum):
    IDLE = "IDLE"; CAPTURE = "CAPTURE"; INTERPRET = "INTERPRET"

@dataclass
class ListenerConfig:
    scheduler_addr: str = "127.0.0.1:50070"
    min_conf: float = 0.5
    timezone: str = "Asia/Yerevan"   # adjust if you prefer

class ListenerDaemon:
    def __init__(
        self,
        wake: WakeDetector,
        vad: VAD,
        asr: ASR,
        planner: Planner,
        cfg: ListenerConfig,
    ) -> None:
        self.wake = wake; self.vad = vad; self.asr = asr; self.planner = planner; self.cfg = cfg
        self._log = logging.getLogger("Listener")
        self._ring: list[AudioFrame] = []  # placeholder pre-roll

    async def run(self) -> None:
        self._log.info("Connecting to scheduler at %s", self.cfg.scheduler_addr)
        async with SchedulerClient(self.cfg.scheduler_addr) as sched:
            while True:
                self._log.debug("State=%s", State.IDLE.value)
                await self.wake.wait_for_hotword()

                self._log.debug("State=%s", State.CAPTURE.value)
                frames = await self.vad.stream_until_eou(self._ring)

                self._log.debug("State=%s", State.INTERPRET.value)
                transcript, conf = await self.asr.transcribe(frames)
                if not transcript or conf < self.cfg.min_conf:
                    await sched.schedule_toolcall_now(ToolCallModel.from_action("speak", {"text": "Sorry, I didn’t catch that."}), timezone=self.cfg.timezone)
                    continue

                plan = await self.planner.plan(transcript)

                # (Optional) quick ack via scheduler so we never overlap audio
                await sched.schedule_toolcall_now(ToolCallModel.from_action("speak", {"text": "Okay."}), timezone=self.cfg.timezone)

                # Schedule all actions via the scheduler
                for action in plan.actions:
                    call = ToolCallModel.from_action(action.tool, action.args)
                    when = (action.when or "now").strip().lower()
                    if when == "now":
                        await sched.schedule_toolcall_now(call, timezone=self.cfg.timezone)
                    else:
                        await sched.schedule_toolcall_when(call, when=when, timezone=self.cfg.timezone)

# ===============================
#              main
# ===============================
async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = ListenerConfig()
    daemon = ListenerDaemon(
        wake=MockWakeDetector(),
        vad=MockVAD(),
        asr=MockASR(),
        planner=MockPlanner(),  # swap with your real LLM planner
        cfg=cfg,
    )
    await daemon.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
