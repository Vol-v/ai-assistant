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
from pyserver.llm.models import ToolCallModel, TaskModel, Tools,SpeakArgsModel,TimerArgsModel,PlaySoundArgsModel
from pyserver.llm.llm import toolcall_from_text
from pyserver.clients.scheduler.client import SchedulerClient

from llm.models import ToolCallModel,TaskModel
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
        cfg: ListenerConfig,
    ) -> None:
        self.wake = wake
        self.vad = vad
        self.asr = asr
        self.cfg = cfg
        self._log = logging.getLogger("Listener")
        self._ring: list[AudioFrame] = []  # pre-roll placeholder

    async def run(self) -> None:
        self._log.info("Connecting to scheduler at %s", self.cfg.scheduler_addr)
        async with SchedulerClient(self.cfg.scheduler_addr, timezone=self.cfg.timezone) as sched:
            while True:
                # IDLE
                self._log.debug("State=%s", State.IDLE.value)
                await self.wake.wait_for_hotword()

                # CAPTURE
                self._log.debug("State=%s", State.CAPTURE.value)
                frames = await self.vad.stream_until_eou(self._ring)

                # INTERPRET
                self._log.debug("State=%s", State.INTERPRET.value)
                transcript, conf = await self.asr.transcribe(frames)
                if not transcript or conf < self.cfg.min_conf:
                    await sched.schedule_toolcall_now(
                        ToolCallModel(speak=SpeakArgsModel(text="Sorry, I didn’t catch that."))
                    )
                    continue

                # LLM → ToolCallModel
                toolcall = toolcall_from_text(transcript)
                which = toolcall.which()

                # Route by tool type
                if which == Tools.SPEAK:
                    # Just schedule speak via scheduler
                    await sched.schedule_toolcall_now(toolcall)

                elif which == Tools.TIMER:
                    # 1) Speak acknowledgement now
                    minutes = toolcall.timer.minutes
                    ack = ToolCallModel(speak=SpeakArgsModel(text=f"Okay, setting a {minutes} minute timer."))
                    await sched.schedule_toolcall_now(ack)
    
                    # 2) Schedule the timer toolcall for the future
                    await sched.schedule_timer(toolcall, minutes=minutes)

                elif which == Tools.PLAY_SOUND:
                    # Optional: speak ack + play sound now
                    ack = ToolCallModel(speak=SpeakArgsModel(text="Playing sound."))
                    await sched.schedule_toolcall_now(ack)
                    await sched.schedule_toolcall_now(toolcall)
# ===============================
#              main
# ===============================
async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = ListenerConfig()
    daemon = ListenerDaemon(
        wake=MockWakeDetector(),
        vad=MockVAD(),
        asr=MockASR(),
        cfg=cfg,
    )
    await daemon.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass